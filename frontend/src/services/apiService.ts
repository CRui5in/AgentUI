import axios, { AxiosResponse } from 'axios';

/**
 * API 基础配置
 */
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * 创建 axios 实例
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 增加到5分钟
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器
 */
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 */
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      // 处理未授权错误
      console.error('未授权访问');
    } else if (error.response?.status === 500) {
      // 处理服务器错误
      console.error('服务器内部错误');
    }
    return Promise.reject(error);
  }
);

/**
 * 任务相关接口
 */
export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  tool_type: string;
  parameters: Record<string, any>;
  result?: any;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

/**
 * 任务统计接口
 */
export interface TaskStats {
  total: number;
  completed: number;
  pending: number;
  failed: number;
}

/**
 * 创建任务请求接口
 */
export interface CreateTaskRequest {
  title: string;
  description: string;
  tool_type: string;
  parameters: Record<string, any>;
}

/**
 * API 服务类
 * 提供与后端 API 交互的方法
 */
class ApiService {
  /**
   * 获取任务列表
   * @param toolType 可选的工具类型过滤
   * @returns 任务列表
   */
  async getTasks(toolType?: string): Promise<AxiosResponse<Task[]>> {
    const params = toolType ? { tool_type: toolType } : {};
    return apiClient.get('/api/tasks/', { params });
  }

  /**
   * 获取单个任务详情
   * @param taskId 任务ID
   * @returns 任务详情
   */
  async getTask(taskId: string): Promise<AxiosResponse<Task>> {
    return apiClient.get(`/api/tasks/${taskId}`);
  }

  /**
   * 创建新任务
   * @param taskData 任务数据
   * @returns 创建的任务
   */
  async createTask(taskData: CreateTaskRequest): Promise<AxiosResponse<Task>> {
    return apiClient.post('/api/tasks/', taskData);
  }

  /**
   * 重试失败的任务
   * @param taskId 任务ID
   * @returns 更新后的任务
   */
  async retryTask(taskId: string): Promise<AxiosResponse<Task>> {
    return apiClient.post(`/api/tasks/${taskId}/retry`);
  }

  /**
   * 取消任务
   * @param taskId 任务ID
   * @returns 更新后的任务
   */
  async cancelTask(taskId: string): Promise<AxiosResponse<Task>> {
    return apiClient.post(`/api/tasks/${taskId}/cancel`);
  }

  /**
   * 删除任务
   * @param taskId 任务ID
   */
  async deleteTask(taskId: string): Promise<AxiosResponse<void>> {
    return apiClient.delete(`/api/tasks/${taskId}`);
  }

  /**
   * 获取任务统计信息
   * @returns 任务统计
   */
  async getTaskStats(): Promise<AxiosResponse<TaskStats>> {
    return apiClient.get('/api/tasks/stats/');
  }

  /**
   * 获取最近任务
   * @param limit 限制数量
   * @returns 最近任务列表
   */
  async getRecentTasks(limit: number = 10): Promise<AxiosResponse<Task[]>> {
    return apiClient.get('/api/tasks/recent/', { params: { limit } });
  }

  /**
   * 获取可用的工具类型
   * @returns 工具类型列表
   */
  async getToolTypes(): Promise<AxiosResponse<string[]>> {
    return apiClient.get('/api/tools/types/');
  }

  /**
   * 获取工具配置
   * @param toolType 工具类型
   * @returns 工具配置
   */
  async getToolConfig(toolType: string): Promise<AxiosResponse<any>> {
    return apiClient.get(`/api/tools/${toolType}/config`);
  }

  /**
   * 健康检查
   * @returns 服务状态
   */
  async healthCheck(): Promise<AxiosResponse<{ status: string; timestamp: string }>> {
    return apiClient.get('/api/system/health/');
  }

  /**
   * 获取系统信息
   * @returns 系统信息
   */
  async getSystemInfo(): Promise<AxiosResponse<any>> {
    return apiClient.get('/api/system/info/');
  }

  /**
   * 下载任务结果文件
   * @param taskId 任务ID
   * @param filename 文件名
   * @returns 文件 blob
   */
  async downloadTaskResult(taskId: string, filename: string): Promise<AxiosResponse<Blob>> {
    return apiClient.get(`/api/tasks/${taskId}/download/${filename}`, {
      responseType: 'blob',
    });
  }

  /**
   * 上传文件
   * @param file 文件对象
   * @param onProgress 上传进度回调
   * @returns 上传结果
   */
  async uploadFile(
    file: File,
    onProgress?: (progressEvent: any) => void
  ): Promise<AxiosResponse<{ filename: string; path: string }>> {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post('/api/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    });
  }

  /**
   * 上传多个文件
   * @param files 文件数组
   * @returns 上传结果
   */
  async uploadFiles(files: File[]): Promise<AxiosResponse<{ files: Array<{ filename: string; path: string }> }>> {
    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append(`files[${index}]`, file);
    });

    return apiClient.post('/api/upload/multiple/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  /**
   * 分析代码库
   * @param data 分析参数
   * @returns 分析结果
   */
  async analyzeCodebase(data: any): Promise<AxiosResponse<any>> {
    return apiClient.post('/api/analyze/codebase/', data);
  }
}

/**
 * 导出 API 服务实例
 */
export const apiService = new ApiService();

/**
 * 导出 axios 实例，供其他模块使用
 */
export { apiClient }; 