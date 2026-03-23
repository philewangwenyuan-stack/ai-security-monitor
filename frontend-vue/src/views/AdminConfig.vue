<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 模拟数据库里的摄像头数据
const cameras = ref([
  { id: 1, name: 'Cam-01 南门', stream_url: 'rtsp://admin:123@192.168.1.10/stream1', interval: 5, active: true },
])

const showAddModal = ref(false)
</script>

<template>
  <div class="min-h-screen bg-[#111827] text-gray-200 p-8 flex flex-col items-center">
    <div class="w-full max-w-6xl">
      <header class="flex justify-between items-center mb-8 border-b border-[#374151] pb-4">
        <h1 class="text-2xl font-bold text-[#60A5FA]">系统后台管理</h1>
        <button @click="router.push('/')" class="text-gray-400 hover:text-white transition-colors">返回大屏</button>
      </header>

      <div class="bg-[#1F2937] border border-[#374151] rounded-xl shadow-xl overflow-hidden">
        <div class="p-4 border-b border-[#374151] flex justify-between items-center bg-[#111827]/50">
          <h2 class="font-semibold text-lg text-white">视频源配置 (RTSP)</h2>
          <button @click="showAddModal = true" class="bg-[#3B82F6] hover:bg-[#60A5FA] text-white px-4 py-2 rounded text-sm font-bold transition-colors">
            + 新增摄像头
          </button>
        </div>

        <table class="w-full text-left text-sm">
          <thead class="bg-[#111827] text-gray-400">
            <tr>
              <th class="p-4">ID</th>
              <th class="p-4">设备名称</th>
              <th class="p-4">流地址 (Stream URL)</th>
              <th class="p-4">抽帧频率</th>
              <th class="p-4">状态</th>
              <th class="p-4 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cam in cameras" :key="cam.id" class="border-b border-[#374151] hover:bg-[#374151]/30">
              <td class="p-4">{{ cam.id }}</td>
              <td class="p-4 font-bold text-[#60A5FA]">{{ cam.name }}</td>
              <td class="p-4 text-gray-400 font-mono text-xs">{{ cam.stream_url }}</td>
              <td class="p-4">{{ cam.interval }} 秒/帧</td>
              <td class="p-4">
                <span class="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400 border border-green-500/50">启用</span>
              </td>
              <td class="p-4 text-right space-x-3">
                <button class="text-[#60A5FA] hover:underline">编辑</button>
                <button class="text-[#EF4444] hover:underline">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>