const CACHE_NAME = 'ibn-alshaikh-store-v1';
// قائمة الصفحات والتصميمات التي سيتم حفظها في جهازك لتعمل أوفلاين
const ASSETS_TO_CACHE = [
    '/dashboard',
    '/sales',
    '/items',
    '/dashboard_stats',
    '/returns',
    '/static/css/style.css', // استبدله بمسار ملفات التنسيق لديك
    '/static/js/main.js'
];

// تثبيت ملف التحكم وحفظ الصفحات في كاش الجهاز
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// اعتراض طلبات الشبكة وتشغيل الصفحات محلياً عند انقطاع النت
self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then((cachedResponse) => {
            return cachedResponse || fetch(e.request).catch(() => {
                // إذا فشل النت والصفحة غير مخزنة (أمان إضافي)
                return caches.match('/dashboard');
            });
        })
    );
});
