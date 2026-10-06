import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({plugins:[react()],resolve:{alias:{'@':fileURLToPath(new URL('.',import.meta.url))}},server:{host:'127.0.0.1',port:5173,proxy:{'/api':{target:'http://127.0.0.1:8000',changeOrigin:true,rewrite:path=>path.replace(/^\/api/,'')},'/measure':{target:'http://127.0.0.1:8001',changeOrigin:true}}},build:{outDir:'dist'}});
