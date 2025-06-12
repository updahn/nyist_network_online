/**
 * 主题切换功能
 * 负责处理网站主题的切换和保存
 */
(function () {
  // 立即执行防止闪烁
  const savedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
    document.body.classList.add('dark-mode');
  } else {
    document.body.classList.remove('dark-mode');
  }

  // 等待文档加载完成
  document.addEventListener('DOMContentLoaded', function () {
    // DOM 元素
    const lightButton = document.querySelector('.theme-option[data-theme="light"]');
    const darkButton = document.querySelector('.theme-option[data-theme="dark"]');

    // 立即应用主题更新按钮状态
    applyTheme();

    // 事件监听
    if (lightButton) {
      lightButton.addEventListener('click', function () {
        setTheme('light');
      });
    }

    if (darkButton) {
      darkButton.addEventListener('click', function () {
        setTheme('dark');
      });
    }

    // 监听系统主题变化
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    prefersDarkScheme.addEventListener('change', function (e) {
      // 只有在用户没有明确设置主题时才跟随系统
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light', false);
      }
    });

    // 应用主题
    function applyTheme() {
      const savedTheme = localStorage.getItem('theme');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

      // 使用保存的主题或跟随系统偏好
      if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        applyDarkTheme();
      } else {
        applyLightTheme();
      }
    }

    // 设置主题并保存偏好
    function setTheme(theme, savePreference = true) {
      if (theme === 'dark') {
        applyDarkTheme();
      } else {
        applyLightTheme();
      }

      // 保存用户偏好到本地存储
      if (savePreference) {
        localStorage.setItem('theme', theme);
      }
    }

    // 应用亮色主题
    function applyLightTheme() {
      document.body.classList.remove('dark-mode');
      if (lightButton && darkButton) {
        lightButton.classList.add('active');
        darkButton.classList.remove('active');
      }
      // 触发主题变更事件，供其他脚本使用
      document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: 'light' } }));
    }

    // 应用暗色主题
    function applyDarkTheme() {
      document.body.classList.add('dark-mode');
      if (lightButton && darkButton) {
        lightButton.classList.remove('active');
        darkButton.classList.add('active');
      }
      // 触发主题变更事件，供其他脚本使用
      document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: 'dark' } }));
    }
  });
})();
