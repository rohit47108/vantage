import { defineConfig } from 'vite';
export default defineConfig({optimizeDeps:{entries:['index.html']},server:{proxy:{'/v1':'http://127.0.0.1:8000'}}});
