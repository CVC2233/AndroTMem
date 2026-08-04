import axios from 'axios';

// const baseURL = '/api';
const baseURL = import.meta.env.VITE_API_BASE_URL;
const instance = axios.create({
    baseURL: baseURL
});
// 定义get方法
async function get(url, params = {}) {

    try {
        const response = await instance.get(url, { params });
        return response.data;
    } catch (error) {
        console.error(`GET ${url} 请求失败`, error);
        throw error;
    }
}

// 定义post方法
async function post(url, data = {}) {
    const headers = {
        'Content-Type': 'application/json',
    };
    try {
        const response = await instance.post(url, data,{headers: headers});
        return response.data;
    } catch (error) {
        console.error(`POST ${url} 请求失败`, error);
        throw error;
    }
}

// 统一导出
export { get, post };