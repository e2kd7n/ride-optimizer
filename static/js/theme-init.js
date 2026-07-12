/**
 * theme-init.js - Applies the saved (or system-preferred) Day/Night theme
 * before first paint. Must load synchronously in <head>, before any CSS
 * that reads data-theme, to avoid a flash of the wrong theme (#470).
 */
(function () {
    try {
        var t = localStorage.getItem('fairWeatherTheme');
        if (t !== 'day' && t !== 'night') {
            t = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'night' : 'day';
        }
        document.documentElement.setAttribute('data-theme', t);
    } catch (e) {}
})();
