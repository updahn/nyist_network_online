/**
 * 工具函数模块
 */
const Utils = {
  // 添加一个静态数组来跟踪当前显示的所有通知
  toasts: [],
  toastBottomOffset: 30, // 初始底部偏移量

  /**
   * 显示成功通知
   * @param {string} message - 通知消息
   */
  showSuccessToast(message) {
    this.showToast(message, 'success');
  },

  /**
   * 显示错误通知
   * @param {string} message - 通知消息
   */
  showErrorToast(message) {
    this.showToast(message, 'error');
  },

  /**
   * 显示通知
   * @param {string} message - 通知消息
   * @param {string} type - 通知类型
   */
  showToast(message, type) {
    // 直接创建一个独立的toast元素
    const toast = document.createElement('div');
    toast.className = 'toast-notification';

    // 计算当前toast的位置
    const bottomOffset = this.calculateToastPosition();

    toast.style.cssText = `
      position: fixed;
      bottom: ${bottomOffset}px;
      right: 30px;
      transform: translateX(20px);
      padding: 15px 20px;
      min-width: 300px;
      border-radius: 8px;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 100000;
      opacity: 0;
      transition: all 0.3s ease;
      font-size: 18px;
      font-weight: 500;
    `;

    // 根据类型设置背景色
    if (type === 'success') {
      toast.style.backgroundColor = '#4caf50';
      toast.style.color = 'white';
    } else if (type === 'error') {
      toast.style.backgroundColor = '#f44336';
      toast.style.color = 'white';
    } else {
      toast.style.backgroundColor = '#2196f3';
      toast.style.color = 'white';
    }

    // 设置内容
    toast.innerHTML = `
      <div style="flex-grow: 1;">
        <span>${message}</span>
      </div>
      <button style="background: none; border: none; color: white; font-size: 22px; cursor: pointer; margin-left: 15px; padding: 0 5px;">&times;</button>
    `;

    // 添加到body
    document.body.appendChild(toast);

    // 获取toast高度
    const toastHeight = toast.offsetHeight;

    // 将toast添加到跟踪数组
    this.toasts.push({
      element: toast,
      height: toastHeight,
    });

    // 强制重绘并显示
    setTimeout(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateX(0)';
    }, 10);

    // 关闭按钮事件
    const closeBtn = toast.querySelector('button');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        this.closeToast(toast);
      });
    }

    // 自动关闭 - 10秒
    setTimeout(() => {
      this.closeToast(toast);
    }, 10000);
  },

  /**
   * 计算新toast的位置
   * @returns {number} 底部偏移量
   */
  calculateToastPosition() {
    if (this.toasts.length === 0) {
      return this.toastBottomOffset;
    }

    // 计算所有现有toast的高度总和加上间距
    let totalOffset = this.toastBottomOffset;
    for (const toast of this.toasts) {
      totalOffset += toast.height + 10; // 10px是toast之间的间距
    }

    return totalOffset;
  },

  /**
   * 关闭toast并重新排列其他toast
   * @param {HTMLElement} toastElement - 要关闭的toast元素
   */
  closeToast(toastElement) {
    // 查找toast在数组中的索引
    const index = this.toasts.findIndex((t) => t.element === toastElement);

    if (index !== -1) {
      // 获取toast的高度
      const toastHeight = this.toasts[index].height;

      // 从数组中移除
      this.toasts.splice(index, 1);

      // 重新排列剩余的toasts
      for (let i = index; i < this.toasts.length; i++) {
        const t = this.toasts[i].element;
        const currentBottom = parseInt(t.style.bottom);
        t.style.bottom = currentBottom - toastHeight - 10 + 'px'; // 减去关闭的toast高度和间距
      }
    }

    // 淡出动画
    toastElement.style.opacity = '0';
    toastElement.style.transform = 'translateX(20px)';

    // 移除元素
    setTimeout(() => {
      if (toastElement.parentNode) {
        toastElement.parentNode.removeChild(toastElement);
      }
    }, 300);
  },

  /**
   * 格式化日期时间
   * @param {string} dateTimeStr - 日期时间字符串
   * @param {boolean} includeTime - 是否包含时间
   * @returns {string} 格式化后的日期时间
   */
  formatDateTime(dateTimeStr, includeTime = true) {
    if (!dateTimeStr) return '-';

    const date = new Date(dateTimeStr);
    if (isNaN(date.getTime())) return dateTimeStr;

    const now = new Date();
    const diffMinutes = Math.floor((now - date) / (1000 * 60));

    if (diffMinutes < 1) {
      return '刚刚';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}分钟前`;
    } else if (diffMinutes < 60 * 24) {
      const hours = Math.floor(diffMinutes / 60);
      return `${hours}小时前`;
    } else if (diffMinutes < 60 * 24 * 7) {
      const days = Math.floor(diffMinutes / (60 * 24));
      return `${days}天前`;
    } else {
      const year = date.getFullYear();
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      const day = date.getDate().toString().padStart(2, '0');

      if (!includeTime) {
        return `${year}-${month}-${day}`;
      }

      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    }
  },

  /**
   * 格式化文件大小
   * @param {number} bytes - 字节数
   * @returns {string} 格式化后的文件大小
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  /**
   * 格式化时间秒数
   * @param {number} seconds - 秒数
   * @returns {string} 格式化后的时间
   */
  formatSeconds(seconds) {
    if (!seconds || isNaN(seconds)) return '-';

    const days = Math.floor(seconds / (24 * 3600));
    const hours = Math.floor((seconds % (24 * 3600)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    let result = '';
    if (days > 0) result += `${days}天 `;
    if (hours > 0 || days > 0) result += `${hours}小时 `;
    if (minutes > 0 || hours > 0 || days > 0) result += `${minutes}分钟 `;
    result += `${secs}秒`;

    return result;
  },

  /**
   * 设置按钮加载状态
   * @param {HTMLElement} button - 按钮元素
   * @param {boolean} isLoading - 是否处于加载状态
   */
  setButtonLoading(button, isLoading) {
    if (isLoading) {
      button.classList.add('btn-loading');
      button.disabled = true;
    } else {
      button.classList.remove('btn-loading');
      button.disabled = false;
    }
  },

  /**
   * 防抖函数
   * @param {Function} func - 要执行的函数
   * @param {number} wait - 等待时间(ms)
   * @returns {Function} 防抖后的函数
   */
  debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  /**
   * 节流函数
   * @param {Function} func - 要执行的函数
   * @param {number} limit - 限制时间(ms)
   * @returns {Function} 节流后的函数
   */
  throttle(func, limit = 300) {
    let inThrottle;
    return function executedFunction(...args) {
      if (!inThrottle) {
        func(...args);
        inThrottle = true;
        setTimeout(() => {
          inThrottle = false;
        }, limit);
      }
    };
  },
};
