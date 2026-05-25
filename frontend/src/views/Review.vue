<template>
  <div class="review-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <el-icon size="28"><DocumentChecked /></el-icon>
        </div>
        <span class="title">实验数据审查</span>
      </div>

      <div class="nav-items">
        <div class="nav-item active">
          <el-icon><DocumentChecked /></el-icon>
          <span>审查</span>
        </div>
        <div class="nav-item" @click="router.push('/files')">
          <el-icon><Folder /></el-icon>
          <span>文件</span>
        </div>
        <div class="nav-item" @click="router.push('/chat')">
          <el-icon><ChatLineRound /></el-icon>
          <span>对话</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="review-main">
      <div class="review-header">
        <h1>手稿统计一致性审查</h1>
        <p class="subtitle">上传学术论文，自动检测统计报告中的潜在问题</p>
      </div>

      <!-- 上传区域 -->
      <div class="upload-section" v-if="!currentTask">
        <el-upload
          drag
          :action="uploadUrl"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          accept=".docx,.pdf,.tex,.txt,.md"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 DOCX, PDF, TEX, TXT, MD 格式，最大 100MB
            </div>
          </template>
        </el-upload>
      </div>

      <!-- 审查配置 -->
      <div class="config-section" v-if="uploadedFile && !currentTask">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>审查配置</span>
            </div>
          </template>

          <el-form :model="config" label-width="120px">
            <el-form-item label="已上传文件">
              <el-tag size="large">{{ uploadedFile.filename }}</el-tag>
            </el-form-item>

            <el-form-item label="审查领域">
              <el-select v-model="config.domain" placeholder="选择领域">
                <el-option label="通用学术" value="general" />
                <el-option label="LLM & 智能体" value="llm_agent" />
                <el-option label="生物信息学 + ML" value="bioinformatics_ml" />
              </el-select>
            </el-form-item>

            <el-form-item label="双模型校验">
              <el-switch v-model="config.dualModel" />
              <span class="form-tip">启用两个独立模型交叉验证，提高准确性</span>
            </el-form-item>

            <el-form-item label="模型 A" v-if="config.dualModel">
              <el-select v-model="config.modelA">
                <el-option label="Claude Sonnet" value="claude" />
                <el-option label="GPT-4" value="gpt4" />
              </el-select>
            </el-form-item>

            <el-form-item label="模型 B" v-if="config.dualModel">
              <el-select v-model="config.modelB">
                <el-option label="Gemini Pro" value="gemini" />
                <el-option label="DeepSeek" value="deepseek" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" @click="startReview" :loading="submitting">
                <el-icon><DocumentChecked /></el-icon>
                开始审查
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 审查进度 -->
      <div class="progress-section" v-if="currentTask && currentTask.status !== 'completed'">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>审查进度</span>
              <el-tag :type="statusType">{{ statusText }}</el-tag>
            </div>
          </template>

          <el-steps :active="activeStep" finish-status="success">
            <el-step title="提取统计量" description="从手稿中提取 NHST 统计量" />
            <el-step title="完整性检查" description="GRIM / GRIMMER / DEBIT" />
            <el-step title="交叉审查" description="Abstract vs Results vs Tables" />
            <el-step title="生成报告" description="HTML 审查报告" />
          </el-steps>

          <el-progress :percentage="currentTask.progress" :status="progressStatus" />
        </el-card>
      </div>

      <!-- 审查结果 -->
      <div class="result-section" v-if="currentTask && currentTask.status === 'completed'">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>审查结果</span>
              <div>
                <el-button type="primary" @click="downloadReport">
                  <el-icon><Download /></el-icon>
                  下载报告
                </el-button>
                <el-button @click="resetReview">新的审查</el-button>
              </div>
            </div>
          </template>

          <!-- 结果摘要 -->
          <div class="result-summary">
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="stat-card high">
                  <div class="stat-number">{{ resultStats.high }}</div>
                  <div class="stat-label">HIGH 风险</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card medium">
                  <div class="stat-number">{{ resultStats.medium }}</div>
                  <div class="stat-label">MEDIUM 风险</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card low">
                  <div class="stat-number">{{ resultStats.low }}</div>
                  <div class="stat-label">LOW 风险</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card pass">
                  <div class="stat-number">{{ resultStats.pass }}</div>
                  <div class="stat-label">通过</div>
                </div>
              </el-col>
            </el-row>
          </div>

          <!-- 双模型校验结果 -->
          <div class="dual-model-result" v-if="currentTask.result?.dual_model">
            <el-divider>双模型校验结果</el-divider>
            <el-alert
              :title="currentTask.result.dual_model.recommendation"
              :type="currentTask.result.dual_model.consensus === 'agree_pass' ? 'success' : currentTask.result.dual_model.consensus === 'agree_fail' ? 'error' : 'warning'"
              :closable="false"
              show-icon
            />
            <el-row :gutter="20" class="model-comparison">
              <el-col :span="12">
                <el-card>
                  <template #header>
                    <div class="model-header">
                      <span>{{ currentTask.result.dual_model.validator_a.model }}</span>
                      <el-tag :type="currentTask.result.dual_model.validator_a.passed ? 'success' : 'danger'">
                        {{ currentTask.result.dual_model.validator_a.passed ? '通过' : '未通过' }}
                      </el-tag>
                    </div>
                  </template>
                  <div>发现问题: {{ currentTask.result.dual_model.validator_a.issues_count }}</div>
                  <div>置信度: {{ (currentTask.result.dual_model.validator_a.confidence * 100).toFixed(0) }}%</div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>
                    <div class="model-header">
                      <span>{{ currentTask.result.dual_model.validator_b.model }}</span>
                      <el-tag :type="currentTask.result.dual_model.validator_b.passed ? 'success' : 'danger'">
                        {{ currentTask.result.dual_model.validator_b.passed ? '通过' : '未通过' }}
                      </el-tag>
                    </div>
                  </template>
                  <div>发现问题: {{ currentTask.result.dual_model.validator_b.issues_count }}</div>
                  <div>置信度: {{ (currentTask.result.dual_model.validator_b.confidence * 100).toFixed(0) }}%</div>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 详细结果 -->
          <div class="result-details">
            <el-collapse>
              <el-collapse-item title="p 值一致性检查" name="1">
                <div v-for="item in pValueResults" :key="item.id" class="result-item">
                  <el-tag :type="item.status === 'pass' ? 'success' : 'danger'" size="small">
                    {{ item.status === 'pass' ? '✓' : '✗' }}
                  </el-tag>
                  <span class="result-text">{{ item.description }}</span>
                </div>
              </el-collapse-item>

              <el-collapse-item title="GRIM / GRIMMER / DEBIT" name="2">
                <div v-for="item in grimResults" :key="item.id" class="result-item">
                  <el-tag :type="item.status === 'pass' ? 'success' : item.status === 'skip' ? 'info' : 'warning'" size="small">
                    {{ item.status }}
                  </el-tag>
                  <span class="result-text">{{ item.description }}</span>
                </div>
              </el-collapse-item>

              <el-collapse-item title="交叉位置一致性" name="3">
                <div v-for="item in crossResults" :key="item.id" class="result-item">
                  <el-tag :type="item.status === 'pass' ? 'success' : 'warning'" size="small">
                    {{ item.status }}
                  </el-tag>
                  <span class="result-text">{{ item.description }}</span>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

// 状态
const uploadedFile = ref(null)
const currentTask = ref(null)
const submitting = ref(false)
const config = ref({
  domain: 'general',
  dualModel: false,
  modelA: 'claude',
  modelB: 'gemini'
})

// 模拟结果数据
const resultStats = ref({ high: 2, medium: 5, low: 8, pass: 15 })
const pValueResults = ref([
  { id: 1, status: 'fail', description: 't(28)=2.14, p=.04 → computed p=.036, decision consistent' },
  { id: 2, status: 'pass', description: 'F(2,45)=3.89, p<.05 → computed p=.027, consistent' },
  { id: 3, status: 'fail', description: 'r(48)=0.31, p=.03 → computed p=.032, decision FLIP (HIGH)' }
])
const grimResults = ref([
  { id: 1, status: 'pass', description: 'Mean=3.2, n=50, Likert 1-5 → GRIM consistent' },
  { id: 2, status: 'skip', description: 'Mean=24.5, n=30, age (continuous) → SKIP' },
  { id: 3, status: 'fail', description: 'Mean=2.8, SD=0.4, n=25, binary → DEBIT fail (HIGH)' }
])
const crossResults = ref([
  { id: 1, status: 'pass', description: 'Abstract N=120 matches Methods N=120' },
  { id: 2, status: 'warning', description: 'Table 1 Mean=3.2 vs Results Mean=3.3 (rounding?)' }
])

// 计算属性
const uploadUrl = computed(() => `${API_BASE}/file/upload`)
const activeStep = computed(() => {
  if (!currentTask.value) return 0
  const progress = currentTask.value.progress
  if (progress < 25) return 0
  if (progress < 50) return 1
  if (progress < 75) return 2
  return 3
})
const statusType = computed(() => {
  const status = currentTask.value?.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
})
const statusText = computed(() => {
  const status = currentTask.value?.status
  const map = { pending: '等待中', processing: '审查中', completed: '已完成', failed: '失败' }
  return map[status] || status
})
const progressStatus = computed(() => {
  if (currentTask.value?.status === 'failed') return 'exception'
  return ''
})

// 方法
const beforeUpload = (file) => {
  const allowed = ['docx', 'pdf', 'tex', 'txt', 'md']
  const ext = file.name.split('.').pop().toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error('不支持的文件格式')
    return false
  }
  if (file.size > 100 * 1024 * 1024) {
    ElMessage.error('文件大小超过 100MB')
    return false
  }
  return true
}

const handleUploadSuccess = (response) => {
  if (response.success) {
    uploadedFile.value = response.file
    ElMessage.success('上传成功')
  }
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const startReview = async () => {
  if (!uploadedFile.value) {
    ElMessage.warning('请先上传文件')
    return
  }

  submitting.value = true
  try {
    const res = await axios.post(`${API_BASE}/review/tasks`, {
      file_id: uploadedFile.value.id,
      domain: config.value.domain,
      dual_model: config.value.dualModel
    })

    if (res.data.task_id) {
      currentTask.value = {
        id: res.data.task_id,
        status: res.data.status,
        progress: 0
      }
      ElMessage.success('审查任务已提交')
      pollProgress(res.data.task_id)
    }
  } catch (err) {
    ElMessage.error('提交失败: ' + (err.response?.data?.error || err.message))
  } finally {
    submitting.value = false
  }
}

const pollProgress = async (taskId) => {
  const interval = setInterval(async () => {
    try {
      const res = await axios.get(`${API_BASE}/review/tasks/${taskId}`)
      currentTask.value = res.data
      
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        clearInterval(interval)
        if (res.data.status === 'completed') {
          ElMessage.success('审查完成')
          // Update result stats from actual data
          if (res.data.result) {
            updateResultStats(res.data.result)
          }
        } else {
          ElMessage.error('审查失败: ' + res.data.error)
        }
      }
    } catch (err) {
      console.error('Poll error:', err)
    }
  }, 2000)
}

const updateResultStats = (result) => {
  resultStats.value = {
    high: result.grim_issues + result.cross_issues,
    medium: result.domain_issues,
    low: 0,
    pass: result.stats_summary.total_stats - result.grim_issues - result.cross_issues - result.domain_issues
  }
}

const downloadReport = () => {
  if (currentTask.value?.result?.report_url) {
    window.open(`${API_BASE}${currentTask.value.result.report_url}`, '_blank')
  } else {
    ElMessage.warning('报告尚未生成')
  }
}

const resetReview = () => {
  uploadedFile.value = null
  currentTask.value = null
  config.value = {
    domain: 'general',
    dualModel: false,
    modelA: 'claude',
    modelB: 'gemini'
  }
}
</script>

<style scoped>
.review-layout {
  display: flex;
  height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.logo {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.nav-items {
  flex: 1;
  padding: 20px 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: #606266;
  transition: all 0.3s;
}

.nav-item:hover {
  background: #f5f7fa;
  color: #667eea;
}

.nav-item.active {
  background: #e8e8fd;
  color: #667eea;
  font-weight: 500;
}

.review-main {
  flex: 1;
  padding: 40px;
  overflow-y: auto;
}

.review-header {
  text-align: center;
  margin-bottom: 40px;
}

.review-header h1 {
  font-size: 32px;
  color: #303133;
  margin-bottom: 8px;
}

.subtitle {
  color: #909399;
  font-size: 16px;
}

.upload-section {
  max-width: 600px;
  margin: 0 auto 30px;
}

.config-section {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 13px;
}

.progress-section {
  max-width: 800px;
  margin: 0 auto;
}

.result-section {
  max-width: 900px;
  margin: 0 auto;
}

.result-summary {
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
  padding: 24px;
  border-radius: 12px;
  color: white;
}

.stat-card.high { background: linear-gradient(135deg, #f56c6c, #e6a23c); }
.stat-card.medium { background: linear-gradient(135deg, #e6a23c, #67c23a); }
.stat-card.low { background: linear-gradient(135deg, #67c23a, #409eff); }
.stat-card.pass { background: linear-gradient(135deg, #409eff, #909399); }

.stat-number {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}

.dual-model-result {
  margin: 20px 0;
}

.model-comparison {
  margin-top: 20px;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.result-text {
  color: #606266;
  font-size: 14px;
}
</style>
