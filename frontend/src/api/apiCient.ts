import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
  AxiosRequestHeaders,
} from "axios";
import { trimPrefix } from "@/util/str";

class APIClient {
  private axiosInstance: AxiosInstance;
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;

    this.axiosInstance = axios.create({
      timeout: 10000,
    });

    this.axiosInstance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("authToken");
        if (!config.headers) {
          config.headers = {} as AxiosRequestHeaders;
        }
        if (token) {
          config.headers["Authorization"] = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    this.axiosInstance.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError) => Promise.reject(error),
    );
  }

  static make(baseUrl: string) {
    return new this(baseUrl);
  }

  private generateUrl(path: string): string {
    const isBaseUrlSlashSuffix = this.baseUrl.endsWith("/");
    const isPathSlashPrefix = path.startsWith("/");

    if (isBaseUrlSlashSuffix && isPathSlashPrefix) {
      return `${this.baseUrl}${trimPrefix(path, "/")}`;
    }

    if (
      (!isBaseUrlSlashSuffix && isPathSlashPrefix) ||
      (isBaseUrlSlashSuffix && !isPathSlashPrefix)
    ) {
      return `${this.baseUrl}${path}`;
    }

    return `${this.baseUrl}/${path}`;
  }

  public async get<T = any>(
    path: string,
    config?: AxiosRequestConfig,
  ): Promise<T>;

  public async get<T = any>(
    path: string,
    config: AxiosRequestConfig | undefined,
    fullResponse: true,
  ): Promise<AxiosResponse<T>>;

  public async get<T>(
    path: string,
    config?: AxiosRequestConfig,
    fullResponse?: true,
  ) {
    const url = this.generateUrl(path);
    const response = await this.axiosInstance.get<T>(url, config);
    if (fullResponse) {
      return response;
    }
    return response.data;
  }

  public async post<T = any, D = any>(
    path: string,
    data?: D,
    config?: AxiosRequestConfig,
  ): Promise<T>;

  public async post<T = any, D = any>(
    path: string,
    data: D | undefined,
    config: AxiosRequestConfig | undefined,
    fullResponse: true,
  ): Promise<AxiosResponse<T>>;

  public async post<T = any, D = any>(
    path: string,
    data?: D,
    config?: AxiosRequestConfig,
    fullResponse?: boolean,
  ): Promise<T | AxiosResponse<T>> {
    const url = this.generateUrl(path);
    const response = await this.axiosInstance.post<T>(url, data, config);

    if (fullResponse) {
      return response;
    }
    return response.data;
  }

  public async put<T = any, D = any>(
    path: string,
    data?: D,
    config?: AxiosRequestConfig,
  ): Promise<T>;

  public async put<T = any, D = any>(
    path: string,
    data: D | undefined,
    config: AxiosRequestConfig | undefined,
    fullResponse: true,
  ): Promise<AxiosResponse<T>>;

  public async put<T = any, D = any>(
    path: string,
    data?: D,
    config?: AxiosRequestConfig,
    fullResponse?: boolean,
  ): Promise<T | AxiosResponse<T>> {
    const url = this.generateUrl(path);
    const response = await this.axiosInstance.put<T>(url, data, config);
    if (fullResponse) {
      return response;
    }
    return response.data;
  }

  public async patch<T = any, D = any>(
    path: string,
    data?: D,
    config?: AxiosRequestConfig,
  ): Promise<T>;

  public async patch<T = any, D = any>(
    path: string,
    data: D | undefined,
    config: AxiosRequestConfig | undefined,
    fullResponse: true,
  ): Promise<AxiosResponse<T>>;

  public async patch<T = any, D = any>(
    path: string,
    data?: D,
    config?: AxiosRequestConfig,
    fullResponse?: boolean,
  ): Promise<T | AxiosResponse<T>> {
    const url = this.generateUrl(path);
    const response = await this.axiosInstance.patch<T>(url, data, config);
    if (fullResponse) {
      return response;
    }
    return response.data;
  }

  public async delete<T = any>(
    path: string,
    config?: AxiosRequestConfig,
  ): Promise<T>;

  public async delete<T = any>(
    path: string,
    config: AxiosRequestConfig | undefined,
    fullResponse: true,
  ): Promise<AxiosResponse<T>>;

  public async delete<T>(
    path: string,
    config?: AxiosRequestConfig,
    fullResponse?: true,
  ): Promise<T | AxiosResponse<T>> {
    const url = this.generateUrl(path);
    const response = await this.axiosInstance.delete<T>(url, config);
    if (fullResponse) {
      return response;
    }
    return response.data;
  }
}

export { APIClient };
