<template>
  <div class="error-page">
    <div class="err-code">{{ code }}</div>
    <div class="err-title">{{ code === 403 ? '无访问权限' : '页面不存在' }}</div>
    <div class="err-desc">{{ code === 403 ? '您没有权限访问此页面，请联系管理员。' : '您访问的页面不存在，请检查地址是否正确。' }}</div>
    <button class="back-btn" @click="$router.push('/sales')">返回首页</button>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ code?: number }>(), { code: 404 })
</script>

<style scoped>
.error-page { width:100vw;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--bg); }
.err-code   { font-size:96px;font-weight:900;color:var(--green);line-height:1; }
.err-title  { font-size:24px;font-weight:800;color:var(--text1);margin:12px 0 8px; }
.err-desc   { font-size:14px;color:var(--text2);margin-bottom:28px; }
.back-btn   { padding:12px 32px;border-radius:12px;background:var(--green);color:#fff;font-size:15px;font-weight:700;border:none;cursor:pointer;transition:background .2s; }
.back-btn:hover { background:var(--green-dark); }
</style>
