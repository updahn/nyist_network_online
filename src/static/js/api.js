/**
 * API调用管理模块
 */
const PRE_URL = '/network'; // 添加 PRE_URL 常量

const API = {
  /**
   * 带超时功能的网络请求
   * @param {string} url - 请求URL
   * @param {object} options - 请求选项
   * @param {number} timeout - 超时时间(ms)
   * @returns {Promise} 请求响应Promise
   */
  async fetchWithTimeout(url, options, timeout = 20000) {
    // 为所有请求添加 PRE_URL 前缀，除非已经包含此前缀
    const fullUrl = url.startsWith(PRE_URL) ? url : `${PRE_URL}${url}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const signal = controller.signal;
    options = options || {};
    options.signal = signal;

    try {
      const response = await Promise.race([fetch(fullUrl, options), new Promise((_, reject) => setTimeout(() => reject(new Error('请求超时，请稍后重试')), timeout))]);
      clearTimeout(timeoutId);

      // 检查HTTP状态码
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`资源不存在 (${response.status}): ${fullUrl}`);
        }
        throw new Error(`请求失败 (${response.status}): ${fullUrl}`);
      }

      return response.json();
    } catch (error) {
      console.error('API请求错误:', error);
      throw error;
    }
  },

  // 设备相关API
  devices: {
    /**
     * 获取用户设备列表
     */
    async getDevices() {
      return API.fetchWithTimeout('/api/devices', {
        method: 'GET',
      });
    },

    /**
     * 添加新设备
     * @param {object} deviceData - 设备信息对象
     */
    async addDevice(deviceData) {
      return API.fetchWithTimeout('/api/device/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(deviceData),
      });
    },

    /**
     * 检查设备状态
     * @param {string} deviceId - 设备ID
     */
    async checkDevice(deviceId) {
      return API.fetchWithTimeout(`/api/device/${deviceId}/check`, {
        method: 'POST',
      });
    },

    /**
     * 登录设备
     * @param {string} deviceId - 设备ID
     */
    async loginDevice(deviceId) {
      return API.fetchWithTimeout(`/api/device/${deviceId}/login`, {
        method: 'POST',
      });
    },

    /**
     * 登出设备
     * @param {string} deviceId - 设备ID
     */
    async logoutDevice(deviceId) {
      return API.fetchWithTimeout(`/api/device/${deviceId}/logout`, {
        method: 'POST',
      });
    },

    /**
     * 删除设备
     * @param {string} deviceId - 设备ID
     */
    async deleteDevice(deviceId) {
      return API.fetchWithTimeout(`/api/device/${deviceId}/delete`, {
        method: 'POST',
      });
    },

    /**
     * 刷新设备列表
     */
    async refreshDevices() {
      return API.fetchWithTimeout('/api/devices/refresh', {
        method: 'POST',
      });
    },

    /**
     * 更新设备信息
     * @param {string} deviceId - 设备ID
     * @param {object} updateData - 更新的数据
     */
    async updateDevice(deviceId, updateData) {
      if (updateData.name) {
        // 如果是更新设备名称
        return API.fetchWithTimeout(`/api/device/${deviceId}/name`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updateData),
        });
      } else if (updateData.network_account_id) {
        // 如果是设置设备账号
        return API.fetchWithTimeout(`/api/device/${deviceId}/account`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ account_id: updateData.network_account_id }),
        });
      }
    },
  },

  // 账号相关API
  accounts: {
    /**
     * 获取用户所有校园网账号
     */
    async getAccounts() {
      return API.fetchWithTimeout('/api/accounts', {
        method: 'GET',
      });
    },

    /**
     * 获取单个账号详情
     * @param {string} accountId - 账号ID
     */
    async getAccount(accountId) {
      return API.fetchWithTimeout(`/api/account/${accountId}`, {
        method: 'GET',
      });
    },

    /**
     * 添加新账号
     * @param {object} accountData - 账号信息
     */
    async addAccount(accountData) {
      return API.fetchWithTimeout('/api/account/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(accountData),
      });
    },

    /**
     * 更新账号信息
     * @param {string} accountId - 账号ID
     * @param {object} updateData - 更新的数据
     */
    async updateAccount(accountId, updateData) {
      return API.fetchWithTimeout(`/api/account/${accountId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
    },

    /**
     * 删除账号
     * @param {string} accountId - 账号ID
     */
    async deleteAccount(accountId) {
      return API.fetchWithTimeout(`/api/account/${accountId}/delete`, {
        method: 'POST',
      });
    },

    /**
     * 设置默认账号
     * @param {string} accountId - 账号ID
     */
    async setDefaultAccount(accountId) {
      return API.fetchWithTimeout(`/api/account/${accountId}/default`, {
        method: 'POST',
      });
    },
  },

  // 用户相关API
  users: {
    /**
     * 用户登录
     * @param {object} credentials - 登录凭据
     */
    async login(credentials) {
      return API.fetchWithTimeout('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });
    },

    /**
     * 用户注册
     * @param {object} userData - 用户数据
     */
    async register(userData) {
      return API.fetchWithTimeout('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });
    },

    /**
     * 用户登出
     */
    async logout() {
      return API.fetchWithTimeout('/api/auth/logout', {
        method: 'GET',
      });
    },

    /**
     * 切换用户状态（激活/停用）
     * @param {string} userId - 用户ID
     */
    async toggleUserStatus(userId) {
      return API.fetchWithTimeout(`/api/admin/users/${userId}/toggle_status`, {
        method: 'POST',
      });
    },

    /**
     * 切换用户管理员权限
     * @param {string} userId - 用户ID
     */
    async toggleUserAdmin(userId) {
      return API.fetchWithTimeout(`/api/admin/users/${userId}/toggle_admin`, {
        method: 'POST',
      });
    },
  },

  // 管理员API
  admin: {
    /**
     * 获取所有用户
     */
    async getAdminUsers() {
      return API.fetchWithTimeout('/api/admin/users', {
        method: 'GET',
      });
    },

    /**
     * 获取所有账号
     */
    async getAdminAccounts() {
      return API.fetchWithTimeout('/api/admin/accounts', {
        method: 'GET',
      });
    },

    /**
     * 获取所有设备
     */
    async getAdminDevices() {
      return API.fetchWithTimeout('/api/admin/devices', {
        method: 'GET',
      });
    },
  },
};
