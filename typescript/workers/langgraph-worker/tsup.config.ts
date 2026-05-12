import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/index.ts', 'src/run.ts'],
  format: ['esm'],
  outExtension() {
    return {
      js: '.mjs',
    }
  },
  platform: 'node',
  // 注入真正的 require 补丁，这是解决 ESM 打包 CJS 依赖最彻底的方法
  banner: {
    js: `
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
`,
  },
  // 恢复全量打包
  noExternal: [/.*/],
  external: ['minio', 'canvas', 'fsevents'],
  clean: true,
  minify: true,
  dts: true,
  splitting: false,
  shims: false,
})
