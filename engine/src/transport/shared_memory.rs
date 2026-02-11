// Ring Buffer Logic

/*
 * ALPHA SOVEREIGN - ZERO-COPY SHARED MEMORY TRANSPORT
 * =================================================================
 * Component Name: engine/src/transport/shared_memory.rs
 * Core Responsibility: نقل كتل البيانات الضخمة (L3 Market Data) بسرعة الضوء (Performance Pillar).
 * Design Pattern: Ring Buffer over Mapped File
 * Forensic Impact: لا يترك أثراً في سجلات الشبكة. التحقيق يتطلب تحليل تفريغ الذاكرة (Memory Dump).
 * =================================================================
 */

use std::sync::atomic::{AtomicUsize, Ordering};
use std::slice;
use std::mem::size_of;
use tracing::{info, error};
use crate::error::{AlphaResult, AlphaError};

// تعريف الثوابت
const SHM_PATH: &str = "/dev/shm/alpha_fast_lane";
const BUFFER_CAPACITY: usize = 1024 * 1024 * 10; // 10 MB Buffer
const MAGIC_HEADER: u32 = 0xA1BDA1BD; // Magic Number (Alpha)

/// رأس الذاكرة المشتركة (Metadata Header)
/// يجب أن يتطابق هذا الهيكل بتاتاً (Bit-perfect) مع كود Python.
#[repr(C)]
pub struct ShmHeader {
    pub magic: u32,            // للتحقق من أننا نقرأ الملف الصحيح
    pub capacity: usize,       // حجم المخزن المؤقت
    pub write_cursor: AtomicUsize, // مؤشر الكتابة (يتحكم فيه Rust)
    pub read_cursor: AtomicUsize,  // مؤشر القراءة (يتحكم فيه Python)
    pub sequence: AtomicUsize,     // رقم تسلسلي للكشف عن فقدان الحزم
}

/// هيكل الرسالة داخل المخزن (Slot)
#[repr(C)]
struct DataSlot {
    length: u32,
    payload: [u8; 1024], // حجم ثابت لكل رسالة (Fixed Size Slot) للسرعة
}

pub struct SharedMemoryTransport {
    // مؤشر خام لمنطقة الذاكرة (Raw Pointer)
    header: *mut ShmHeader,
    data_ptr: *mut u8,
    
    // الاحتفاظ بمقبض الملف لمنع إغلاقه
    _mmap: memmap2::MmapMut,
}

// تنفيذ Send للتأكد من إمكانية نقل الكائن بين الخيوط (نحن نتحمل مسؤولية الأمان)
unsafe impl Send for SharedMemoryTransport {}
unsafe impl Sync for SharedMemoryTransport {}

impl SharedMemoryTransport {
    /// إنشاء أو فتح منطقة الذاكرة المشتركة
    pub fn new(create_new: bool) -> AlphaResult<Self> {
        use std::fs::OpenOptions;
        use memmap2::MmapMut;

        // 1. فتح الملف (الذي يمثل الذاكرة)
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(create_new)
            .open(SHM_PATH)
            .map_err(|e| AlphaError::BootstrapError(format!("SHM File Open Error: {}", e)))?;

        // تعيين الحجم إذا كنا نحن من ينشئه
        if create_new {
            file.set_len((size_of::<ShmHeader>() + BUFFER_CAPACITY) as u64)
                .map_err(|e| AlphaError::BootstrapError(format!("SHM Truncate Error: {}", e)))?;
        }

        // 2. تعيين الذاكرة (Memory Mapping)
        let mut mmap = unsafe { 
            MmapMut::map_mut(&file)
                .map_err(|e| AlphaError::BootstrapError(format!("Mmap Error: {}", e)))? 
        };

        // 3. حساب المؤشرات
        let base_ptr = mmap.as_mut_ptr();
        let header_ptr = base_ptr as *mut ShmHeader;
        
        // مؤشر البيانات يبدأ بعد الـ Header مباشرة
        let data_offset = size_of::<ShmHeader>();
        let data_ptr = unsafe { base_ptr.add(data_offset) };

        // 4. تهيئة الرأس (إذا كان جديداً)
        if create_new {
            unsafe {
                (*header_ptr).magic = MAGIC_HEADER;
                (*header_ptr).capacity = BUFFER_CAPACITY;
                (*header_ptr).write_cursor = AtomicUsize::new(0);
                (*header_ptr).read_cursor = AtomicUsize::new(0);
                (*header_ptr).sequence = AtomicUsize::new(0);
            }
            info!("SHM: Initialized new shared memory region at {}", SHM_PATH);
        } else {
            // التحقق من الـ Magic
            unsafe {
                if (*header_ptr).magic != MAGIC_HEADER {
                    return Err(AlphaError::Fatal("SHM Magic Mismatch! Possible memory corruption.".into()));
                }
            }
        }

        Ok(Self {
            header: header_ptr,
            data_ptr,
            _mmap: mmap,
        })
    }

    /// كتابة بيانات (Zero-Copy-ish)
    /// نحن نكتب مباشرة في الـ RAM المخصصة لـ Python.
    pub fn write_bytes(&self, data: &[u8]) -> AlphaResult<()> {
        if data.len() > 1024 {
            return Err(AlphaError::Internal("Data too large for SHM slot".into()));
        }

        unsafe {
            let header = &*self.header;
            
            // 1. حساب الموقع في الحلقة (Ring Buffer Logic)
            let current_write = header.write_cursor.load(Ordering::Acquire);
            let next_write = (current_write + 1) % (BUFFER_CAPACITY / size_of::<DataSlot>());
            
            // التحقق من الامتلاء (هل الكتابة ستتجاوز القراءة؟)
            let current_read = header.read_cursor.load(Ordering::Acquire);
            if next_write == current_read {
                // Buffer Full - Drop Strategy or Spin Wait?
                // في HFT، نفضل إسقاط القديم (Drop Oldest) أو التحذير، الانتظار يعني الموت.
                // هنا سنقوم برمي خطأ للتبسيط.
                return Err(AlphaError::Internal("SHM Ring Buffer Full! Python is too slow.".into()));
            }

            // 2. الوصول للموقع في الذاكرة
            let slot_ptr = (self.data_ptr as *mut DataSlot).add(current_write);
            
            // 3. كتابة البيانات (Memcpy سريع جداً داخل الـ CPU Cache)
            (*slot_ptr).length = data.len() as u32;
            std::ptr::copy_nonoverlapping(data.as_ptr(), (*slot_ptr).payload.as_mut_ptr(), data.len());

            // 4. تحديث المؤشرات (Commit)
            // نستخدم Release لضمان أن البيانات كتبت فعلاً قبل تحديث المؤشر
            header.sequence.fetch_add(1, Ordering::Release);
            header.write_cursor.store(next_write, Ordering::Release);
        }

        Ok(())
    }

    /// قراءة الإحصائيات (للمراقبة)
    pub fn get_stats(&self) -> String {
        unsafe {
            let header = &*self.header;
            format!(
                "SHM Stats [Seq: {}, Write: {}, Read: {}, Lag: {}]", 
                header.sequence.load(Ordering::Relaxed),
                header.write_cursor.load(Ordering::Relaxed),
                header.read_cursor.load(Ordering::Relaxed),
                // حساب الفرق (Lag)
                (header.write_cursor.load(Ordering::Relaxed) + 1000 - header.read_cursor.load(Ordering::Relaxed)) % 1000 // تقريبي
            )
        }
    }
}