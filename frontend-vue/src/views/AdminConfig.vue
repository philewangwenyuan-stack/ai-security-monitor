<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const cameras = ref<any[]>([])
const loading = ref(false)

// 弹窗状态
const isModalOpen = ref(false)
const modalMode = ref<'add' | 'edit'>('add')
// 包含了数据库中真实的字段：stream_url 和 capture_interval
const currentCamera = ref({ id: 0, name: '', stream_url: '', capture_interval: 5 })

// 1. 获取摄像头列表
const fetchCameras = async () => {
  loading.value = true
  try {
    const res = await fetch('http://127.0.0.1:8000/api/config/cameras')
    cameras.value = await res.json()
  } catch (error) {
    console.error("加载失败", error)
  }
  loading.value = false
}

onMounted(() => {
  fetchCameras()
})

// 2. 打开弹窗 (新增/编辑)
const openModal = (mode: 'add' | 'edit', cam?: any) => {
  modalMode.value = mode
  if (mode === 'edit' && cam) {
    currentCamera.value = { ...cam }
  } else {
    // 默认给 5 秒的抽帧间隔
    currentCamera.value = { id: 0, name: '', stream_url: '', capture_interval: 5 }
  }
  isModalOpen.value = true
}

// 3. 提交表单 (对接后端 POST/PUT)
const saveCamera = async () => {
  if (!currentCamera.value.name || !currentCamera.value.stream_url) {
    alert("名称和地址不能为空！")
    return
  }
  
  try {
    const method = modalMode.value === 'add' ? 'POST' : 'PUT'
    const url = modalMode.value === 'add' 
      ? 'http://127.0.0.1:8000/api/config/cameras' 
      : `http://127.0.0.1:8000/api/config/cameras/${currentCamera.value.id}`

    await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: currentCamera.value.name,
        stream_url: currentCamera.value.stream_url, // 对接数据库字段
        capture_interval: Number(currentCamera.value.capture_interval), // 对接间隔字段
        is_active: true
      })
    })

    isModalOpen.value = false
    await fetchCameras() // 刷新列表
  } catch (error) {
    alert("保存失败，请检查控制台")
  }
}

// 4. 删除摄像头 (对接后端 DELETE)
const deleteCamera = async (id: number) => {
  if (!confirm("确定要删除这个摄像头吗？删除后视频流将立即停止。")) return
  
  try {
    await fetch(`http://127.0.0.1:8000/api/config/cameras/${id}`, { method: 'DELETE' })
    await fetchCameras() // 刷新列表
  } catch (error) {
    alert("删除失败")
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#111827] text-gray-200 p-8 font-sans">
    <div class="max-w-6xl mx-auto">
      
      <header class="flex justify-between items-center mb-8 border-b border-[#374151] pb-4">
        <div>
          <h1 class="text-3xl font-extrabold text-white tracking-wider">系统配置中心</h1>
          <p class="text-gray-400 text-sm mt-1">管理视频源与系统参数设置</p>
        </div>
        <button @click="router.push('/')" class="px-5 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md transition-colors shadow-lg font-semibold text-sm">
          返回监控大屏
        </button>
      </header>

      <div class="bg-[#1F2937] rounded-xl border border-[#374151] shadow-2xl p-6">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-xl font-bold text-[#60A5FA]">摄像头数据源管理</h2>
          <button @click="openModal('add')" class="px-4 py-2 bg-[#3B82F6] hover:bg-blue-500 text-white rounded font-medium flex items-center gap-2 transition-colors">
            <span>+ 新增摄像头</span>
          </button>
        </div>

        <div class="overflow-x-auto rounded-lg border border-[#374151]">
          <table class="w-full text-left text-sm text-gray-400">
            <thead class="bg-[#111827] text-gray-300 uppercase font-semibold">
              <tr>
                <th class="px-6 py-4">ID</th>
                <th class="px-6 py-4">监控点名称</th>
                <th class="px-6 py-4">RTSP / 视频流地址</th>
                <th class="px-6 py-4">AI 分析间隔</th>
                <th class="px-6 py-4 text-right">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#374151] bg-[#1F2937]">
              <tr v-if="loading"><td colspan="5" class="text-center py-8">加载中...</td></tr>
              <tr v-else-if="cameras.length === 0"><td colspan="5" class="text-center py-8">暂无配置摄像头</td></tr>
              <tr v-for="cam in cameras" :key="cam.id" class="hover:bg-[#374151]/30 transition-colors">
                <td class="px-6 py-4 font-mono">{{ cam.id }}</td>
                <td class="px-6 py-4 font-bold text-gray-200">{{ cam.name }}</td>
                <td class="px-6 py-4 font-mono text-xs text-blue-400 break-all">{{ cam.stream_url }}</td>
                <td class="px-6 py-4 font-mono text-xs text-gray-400">{{ cam.capture_interval }} 秒/次</td>
                <td class="px-6 py-4 text-right space-x-3">
                  <button @click="openModal('edit', cam)" class="text-blue-400 hover:text-blue-300 font-medium">编辑</button>
                  <button @click="deleteCamera(cam.id)" class="text-red-400 hover:text-red-300 font-medium">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="isModalOpen" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-[#1F2937] rounded-xl border border-[#374151] shadow-2xl w-full max-w-md overflow-hidden">
        <div class="px-6 py-4 border-b border-[#374151] flex justify-between items-center bg-[#111827]">
          <h3 class="text-lg font-bold text-white">{{ modalMode === 'add' ? '新增摄像头' : '编辑摄像头' }}</h3>
          <button @click="isModalOpen = false" class="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-400 mb-1">监控点位名称</label>
            <input v-model="currentCamera.name" type="text" placeholder="例如: 南门主干道" class="w-full bg-[#111827] border border-[#374151] rounded px-3 py-2 text-white focus:outline-none focus:border-[#60A5FA]" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-400 mb-1">视频流/RTSP地址</label>
            <input v-model="currentCamera.stream_url" type="text" placeholder="rtsp://..." class="w-full bg-[#111827] border border-[#374151] rounded px-3 py-2 text-white focus:outline-none focus:border-[#60A5FA]" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-400 mb-1">AI 抽帧分析间隔 (秒)</label>
            <input v-model="currentCamera.capture_interval" type="number" min="1" class="w-full bg-[#111827] border border-[#374151] rounded px-3 py-2 text-white focus:outline-none focus:border-[#60A5FA]" />
          </div>
        </div>
        <div class="px-6 py-4 border-t border-[#374151] flex justify-end gap-3 bg-[#111827]">
          <button @click="isModalOpen = false" class="px-4 py-2 rounded text-sm text-gray-300 hover:bg-[#374151] transition-colors">取消</button>
          <button @click="saveCamera" class="px-4 py-2 rounded text-sm bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors">确认保存</button>
        </div>
      </div>
    </div>
  </div>
</template>