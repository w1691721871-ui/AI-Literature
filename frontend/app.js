const { computed, createApp, ref } = Vue;

const API_BASE_URL = "https://ai-literature.onrender.com";
const REQUEST_TIMEOUT_MS = 90_000;
const DEFAULT_TASK = "请分析这篇论文的研究主题、研究问题、研究方法、主要结果、创新点和局限性。";
const AGENT_STAGES = [
  "正在读取论文",
  "正在提取论文内容",
  "正在理解用户任务",
  "正在分析论文",
  "正在整理分析结果",
  "分析完成",
];

createApp({
  setup() {
    const task = ref(DEFAULT_TASK);
    const selectedFile = ref(null);
    const fileInput = ref(null);
    const result = ref(null);
    const question = ref("");
    const chatMessages = ref([]);
    const loading = ref(false);
    const asking = ref(false);
    const errorMessage = ref("");
    const agentStageIndex = ref(0);
    const analysisCompleted = ref(false);
    let stageTimers = [];

    const fileSizeLabel = computed(() => {
      if (!selectedFile.value) return "";
      const sizeInMb = selectedFile.value.size / 1024 / 1024;
      return sizeInMb >= 1
        ? `${sizeInMb.toFixed(1)} MB`
        : `${Math.max(1, Math.round(selectedFile.value.size / 1024))} KB`;
    });

    const uploadStatus = computed(() => {
      if (loading.value) return "正在分析";
      if (selectedFile.value) return "文件已就绪";
      return "等待上传";
    });

    const analysisCards = computed(() => {
      if (!result.value?.analysis) return [];
      const analysis = result.value.analysis;
      return [
        { key: "research_topic", title: "研究主题", value: analysis.research_topic },
        { key: "research_question", title: "研究问题", value: analysis.research_question },
        { key: "methodology", title: "研究方法", value: analysis.methodology },
        { key: "key_findings", title: "核心发现", value: analysis.key_findings },
        { key: "innovation_points", title: "创新点", value: analysis.innovation_points },
        { key: "limitations", title: "局限性", value: analysis.limitations },
        { key: "keywords", title: "关键词", value: analysis.keywords, tags: true },
      ];
    });

    function onFileChange(event) {
      selectedFile.value = event.target.files[0] || null;
      errorMessage.value = "";
    }

    function clearStageTimers() {
      stageTimers.forEach((timer) => window.clearTimeout(timer));
      stageTimers = [];
    }

    function startAgentProgress() {
      clearStageTimers();
      agentStageIndex.value = 0;
      analysisCompleted.value = false;

      // The backend has no streaming stage events. These are paced UI hints while
      // one analysis request is in progress, not a claim of real-time server state.
      [400, 900, 1500, 2300].forEach((delay, index) => {
        stageTimers.push(window.setTimeout(() => {
          agentStageIndex.value = index + 1;
        }, delay));
      });
    }

    function finishAgentProgress() {
      clearStageTimers();
      agentStageIndex.value = AGENT_STAGES.length - 1;
      analysisCompleted.value = true;
    }

    async function readResponse(response) {
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("服务器返回异常，请稍后重试。");
      }
      if (!response.ok) {
        if (typeof data.detail === "string") throw new Error(data.detail);
        if (response.status === 503) throw new Error("后端服务暂时不可用，请稍后重试。");
        if (response.status >= 500) throw new Error("服务处理失败，请稍后重试。");
        throw new Error("请求参数不正确，请检查输入后重试。");
      }
      return data;
    }

    async function fetchWithTimeout(url, options) {
      const controller = new AbortController();
      let timedOut = false;
      const timeout = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, REQUEST_TIMEOUT_MS);

      try {
        return await fetch(url, { ...options, signal: controller.signal });
      } catch (error) {
        if (timedOut) throw new Error("请求超时，请稍后重试或上传篇幅更短的论文。");
        if (error instanceof TypeError) {
          throw new Error("无法连接后端服务，请确认后端已启动后重试。");
        }
        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    }

    async function analyzePaper() {
      if (loading.value) return;
      if (!selectedFile.value) {
        errorMessage.value = "请先选择一篇 PDF 文件。";
        return;
      }
      if (!task.value.trim()) {
        errorMessage.value = "请输入分析任务。";
        return;
      }

      loading.value = true;
      errorMessage.value = "";
      result.value = null;
      chatMessages.value = [];
      startAgentProgress();

      try {
        const formData = new FormData();
        formData.append("file", selectedFile.value);
        formData.append("task", task.value.trim());
        const response = await fetchWithTimeout(`${API_BASE_URL}/agent/analyze-paper`, {
          method: "POST",
          body: formData,
        });
        result.value = await readResponse(response);
        finishAgentProgress();
        chatMessages.value.push({
          role: "assistant",
          content: "论文分析已完成。你可以继续针对研究方法、实验设计或结论提问。",
        });
      } catch (error) {
        clearStageTimers();
        errorMessage.value = error.message || "分析请求失败，请稍后重试。";
      } finally {
        loading.value = false;
      }
    }

    async function askQuestion() {
      const normalizedQuestion = question.value.trim();
      if (!normalizedQuestion || !result.value || asking.value) return;

      asking.value = true;
      errorMessage.value = "";
      chatMessages.value.push({ role: "user", content: normalizedQuestion });
      question.value = "";

      try {
        const response = await fetchWithTimeout(
          `${API_BASE_URL}/agent/papers/${result.value.paper_id}/questions`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: normalizedQuestion }),
          },
        );
        const data = await readResponse(response);
        chatMessages.value.push({ role: "assistant", content: data.answer });
      } catch (error) {
        errorMessage.value = error.message || "追问请求失败，请稍后重试。";
        question.value = normalizedQuestion;
      } finally {
        asking.value = false;
      }
    }

    function resetTask() {
      task.value = DEFAULT_TASK;
    }

    function clearCurrentPaper() {
      selectedFile.value = null;
      result.value = null;
      question.value = "";
      chatMessages.value = [];
      errorMessage.value = "";
      clearStageTimers();
      agentStageIndex.value = 0;
      analysisCompleted.value = false;
      if (fileInput.value) fileInput.value.value = "";
    }

    return {
      analysisCards,
      agentStageIndex,
      agentStages: AGENT_STAGES,
      asking,
      analysisCompleted,
      chatMessages,
      clearCurrentPaper,
      errorMessage,
      fileInput,
      fileSizeLabel,
      loading,
      onFileChange,
      askQuestion,
      analyzePaper,
      question,
      resetTask,
      result,
      selectedFile,
      task,
      uploadStatus,
    };
  },
  template: `
    <main class="app-shell">
      <header class="topbar">
        <div>
          <p class="product-mark"><span></span> RESEARCH AI</p>
          <h1>AI 科研文献分析助手</h1>
          <p class="product-description">上传论文，用清晰的结构化视角快速理解研究价值。</p>
        </div>
        <div class="topbar-status"><i></i> Agent 已就绪</div>
      </header>

      <p v-if="errorMessage" class="error-alert" role="alert">
        <span>!</span>{{ errorMessage }}
      </p>

      <section class="workspace-grid">
        <aside class="control-panel">
          <div class="panel-heading">
            <p class="section-kicker">WORKSPACE</p>
            <h2>论文与任务</h2>
          </div>

          <label class="upload-box" :class="{ 'has-file': selectedFile }" for="pdf-file">
            <input ref="fileInput" id="pdf-file" type="file" accept="application/pdf,.pdf" @change="onFileChange" />
            <span class="upload-icon">⇧</span>
            <strong>{{ selectedFile ? "更换 PDF 文件" : "上传论文 PDF" }}</strong>
            <small>支持可提取文本的 PDF</small>
          </label>

          <div class="file-summary" v-if="selectedFile">
            <div class="file-badge">PDF</div>
            <div class="file-details">
              <strong>{{ selectedFile.name }}</strong>
              <span>{{ fileSizeLabel }}</span>
            </div>
            <span class="ready-dot"></span>
          </div>

          <div class="upload-status">
            <span>上传状态</span><strong :class="{ active: selectedFile }">{{ uploadStatus }}</strong>
          </div>

          <div class="task-section">
            <div class="label-row">
              <label for="task">分析任务</label>
              <button class="text-button" type="button" @click="resetTask">恢复默认</button>
            </div>
            <textarea id="task" v-model="task" rows="6"></textarea>
            <p class="field-hint">Agent 会识别任务重点，并选择对应的分析流程。</p>
          </div>

          <button class="analyze-button" :disabled="loading" @click="analyzePaper">
            <span v-if="loading" class="spinner small-spinner"></span>
            {{ loading ? "正在分析论文..." : "开始分析" }}
          </button>
          <button v-if="result" class="clear-button" type="button" @click="clearCurrentPaper">清空当前论文</button>
        </aside>

        <section class="result-panel">
          <div class="result-header">
            <div>
              <p class="section-kicker">ANALYSIS</p>
              <h2>论文分析结果</h2>
            </div>
            <button v-if="result" class="outline-button" :disabled="loading" @click="analyzePaper">重新分析</button>
          </div>

          <div v-if="loading" class="loading-state">
            <div class="process-heading">
              <span class="spinner"></span>
              <div><h3>{{ agentStages[agentStageIndex] }}</h3><p>请求正在处理中，请稍候…</p></div>
            </div>
            <ol class="agent-progress" aria-label="Agent 处理阶段">
              <li v-for="(stage, index) in agentStages.slice(0, 5)" :key="stage" :class="{ active: index === agentStageIndex, done: index < agentStageIndex }">
                <span>{{ index < agentStageIndex ? "✓" : index + 1 }}</span>{{ stage }}
              </li>
            </ol>
            <small class="progress-note">阶段为请求生命周期指引，服务端未提供实时流式状态。</small>
          </div>

          <div v-else-if="!result" class="empty-state">
            <div class="empty-illustration">⌁</div>
            <h3>等待开始分析</h3>
            <p>上传一篇 PDF，设置分析任务后，结果会显示在这里。</p>
          </div>

          <div v-else class="analysis-content">
            <div v-if="analysisCompleted" class="completed-process"><span>✓</span> Agent 已完成论文读取、任务理解、分析与结果整理</div>
            <div class="paper-title-row">
              <div>
                <span class="result-label">论文标题</span>
                <h3>{{ result.analysis.title || "论文未说明" }}</h3>
              </div>
              <span class="status-pill">{{ result.task_type || "论文整体分析" }}</span>
            </div>

            <div class="analysis-grid">
              <article v-for="card in analysisCards" :key="card.key" class="analysis-card" :class="{ 'keyword-card': card.tags }">
                <h3>{{ card.title }}</h3>
                <template v-if="Array.isArray(card.value)">
                  <ul v-if="!card.tags" class="finding-list">
                    <li v-for="item in card.value" :key="item">{{ item }}</li>
                    <li v-if="!card.value.length">论文未说明</li>
                  </ul>
                  <div v-else class="keyword-list">
                    <span v-for="item in card.value" :key="item">{{ item }}</span>
                    <em v-if="!card.value.length">论文未说明</em>
                  </div>
                </template>
                <p v-else>{{ card.value || "论文未说明" }}</p>
              </article>
            </div>
          </div>
        </section>
      </section>

      <section class="chat-panel">
        <div class="chat-header">
          <div>
            <p class="section-kicker">FOLLOW-UP</p>
            <h2>继续追问论文</h2>
          </div>
          <span v-if="result" class="context-note">已连接当前论文</span>
        </div>

        <div v-if="!result" class="chat-empty">完成论文分析后，即可在这里继续对话。</div>
        <div v-else class="messages" aria-live="polite">
          <div v-for="(message, index) in chatMessages" :key="index" class="message-row" :class="message.role">
            <span class="message-avatar">{{ message.role === "user" ? "你" : "AI" }}</span>
            <p>{{ message.content }}</p>
          </div>
          <div v-if="asking" class="message-row assistant thinking-message">
            <span class="message-avatar">AI</span><p><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></p>
          </div>
        </div>

        <div class="chat-composer" :class="{ disabled: !result }">
          <input v-model="question" :disabled="!result || asking" placeholder="例如：这个研究方法有什么优势？" @keyup.enter="askQuestion" />
          <button :disabled="!result || !question.trim() || asking" @click="askQuestion">
            {{ asking ? "思考中" : "发送" }} <span>→</span>
          </button>
        </div>
      </section>
    </main>
  `,
}).mount("#app");
