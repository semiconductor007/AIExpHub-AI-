<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getHealth } from '../api/health'
import GuideIcon from '../components/GuideIcon.vue'
import ProjectEntryPicker from '../components/ProjectEntryPicker.vue'

const state = ref<'loading' | 'healthy' | 'unavailable'>('loading')
const router = useRouter()
const picker = ref<InstanceType<typeof ProjectEntryPicker>>()
const detailsOpen = ref<string[]>([])
const entries = [
  { icon: 'project' as const, title: '项目管理', subtitle: '确定研究主题', description: '创建、编辑实验项目，选择并进入项目。', features: ['项目名称与说明', '项目入口与维护'], path: '/projects', link: '管理实验项目' },
  { icon: 'experiment' as const, title: '项目工作区', subtitle: '记录配置与结果', description: '实验录入和结果维护都在这里。按批次组织实验，统一管理项目指标。', features: ['新建 / 复制 / JSON 导入', '查看详情与录入结果', '批次与共享指标管理'], path: '/experiments', link: '打开项目工作区' },
  { icon: 'compare' as const, title: '实验比较', subtitle: '从数据发现差异', description: '比较多个实验的表现，找出最佳指标，并分析参数变化。', features: ['指标表格、最佳结果与基准差值', '图表展示与 CSV / PNG 导出', '按需生成 AI 总结'], path: '/compare', link: '进入实验比较' },
]
const steps = [
  { icon: 'project' as const, title: '创建项目', text: '确定研究主题', action: () => createProject() },
  { icon: 'batch' as const, title: '建立批次', text: '为一组实验命名', action: () => picker.value?.open('manage-batches') },
  { icon: 'experiment' as const, title: '录入实验', text: '填写模型与参数', action: () => picker.value?.open('new-experiment') },
  { icon: 'result' as const, title: '保存结果', text: '手动录入或导入 JSON', action: () => picker.value?.open() },
  { icon: 'compare' as const, title: '勾选比较', text: '选择至少两个实验', action: () => picker.value?.open() },
  { icon: 'chart' as const, title: '查看分析', text: '图表、导出与 AI 总结', action: () => router.push('/compare') },
]
function createProject(): void { void router.push({ path: '/projects', query: { action: 'create' } }) }
async function checkHealth(): Promise<void> {
  state.value = 'loading'
  try { state.value = (await getHealth()).status === 'ok' ? 'healthy' : 'unavailable' }
  catch { state.value = 'unavailable' }
}
onMounted(checkHealth)
</script>

<template>
  <div class="home-content">
    <section class="hero" aria-labelledby="home-title">
      <div class="hero-copy">
        <span class="eyebrow">AIEXPHUB · 实验记录与分析</span>
        <h1 id="home-title">让每一次实验<br />都有据可比。</h1>
        <p class="hero-description">集中保存模型配置与评测结果，比较不同模型、参数和实验批次的表现，让数据成为下一次实验的起点。</p>
        <div class="hero-actions"><el-button type="primary" size="large" @click="picker?.open('new-experiment')"><GuideIcon name="experiment" :size="18" />新建实验</el-button><el-button size="large" @click="createProject">创建项目</el-button><router-link to="/compare" class="hero-link">比较实验 <span aria-hidden="true">↗</span></router-link></div>
        <p class="hero-note">在外部完成训练与评测，在这里记录配置、保存结果、比较分析。</p>
      </div>
      <div class="hero-visual" aria-hidden="true"><div class="visual-label"><span class="live-dot"></span> 从配置到结论</div><div class="visual-bars"><span></span><span></span><span></span><span></span><span></span></div><div class="visual-tags"><span>模型参数</span><span>评测指标</span><span>实验洞察</span></div><p>记录 · 比较 · 迭代</p></div>
    </section>

    <section class="home-section" aria-labelledby="relationship-title">
      <div class="section-heading"><div><span class="section-kicker">01 / 理解实验结构</span><h2 id="relationship-title">一个研究主题，多组有序实验</h2></div><span class="section-caption">以下为结构示例，非真实实验数据</span></div>
      <div class="relationship-grid">
        <article class="relation-card project-node">
          <div class="node-heading"><span class="icon-box"><GuideIcon name="project" /></span><div><span class="node-en">PROJECT</span><h3>实验项目</h3></div><span class="level-tag">研究主题</span></div>
          <p class="node-description">围绕同一个研究目标，集中管理实验和共享指标。</p>
          <div class="example-card"><span class="example-label">例如</span><strong>中文文本分类评测</strong><div class="metric-pills"><span>准确率</span><span>F1</span><span>推理延迟</span></div></div>
          <p class="node-footnote">可包含多个模型，共用项目的指标定义。</p>
        </article>
        <article class="relation-card batch-node">
          <span class="relation-connector" aria-hidden="true">一对多 <span>→</span></span>
          <div class="node-heading"><span class="icon-box"><GuideIcon name="batch" /></span><div><span class="node-en">BATCH</span><h3>实验批次</h3></div><span class="level-tag">实验分组</span></div>
          <p class="node-description">把同一轮对照或重复验证放在一起，方便组织和筛选。</p>
          <div class="batch-example"><GuideIcon name="batch" :size="18" /><div><strong>学习率对照</strong><span>比较不同学习率的表现</span></div></div>
          <div class="batch-example secondary"><GuideIcon name="batch" :size="18" /><div><strong>重复验证</strong><span>更换随机种子，观察稳定性</span></div></div>
          <p class="node-footnote">只有一组实验时，建一个批次即可。</p>
        </article>
        <article class="relation-card experiment-node">
          <span class="relation-connector" aria-hidden="true">一对多 <span>→</span></span>
          <div class="node-heading"><span class="icon-box"><GuideIcon name="experiment" /></span><div><span class="node-en">EXPERIMENT</span><h3>单次实验</h3></div><span class="level-tag">具体记录</span></div>
          <p class="node-description">记录一次实验使用的模型、参数和对应结果。</p>
          <div class="experiment-example"><div><strong>学习率 0.0001</strong><span class="config-tag">配置</span></div><code>模型 A · batch_size: 32</code><div class="result-slot"><GuideIcon name="result" :size="17" /><span>当前结果</span><small>可稍后录入</small></div></div>
          <p class="node-footnote">最多一份当前结果，修改后用于最新比较。</p>
        </article>
      </div>
      <div class="relationship-footer"><span class="relationship-dot"></span>项目包含批次，批次包含实验。批次用于分组；比较时可以跨批次、跨项目选择实验。</div>
    </section>

    <section class="home-section" aria-labelledby="pages-title">
      <div class="section-heading"><div><span class="section-kicker">02 / 找到操作入口</span><h2 id="pages-title">每个页面，各司其职</h2></div></div>
      <div class="page-grid"><article v-for="entry in entries" :key="entry.path" class="page-card">
        <div class="page-card-heading"><span class="icon-box"><GuideIcon :name="entry.icon" /></span><span>{{ entry.subtitle }}</span></div>
        <h3>{{ entry.title }}</h3><p>{{ entry.description }}</p><ul><li v-for="feature in entry.features" :key="feature"><span aria-hidden="true">✓</span>{{ feature }}</li></ul>
        <router-link :to="entry.path">{{ entry.link }} <span aria-hidden="true">→</span></router-link>
      </article></div>
    </section>

    <section class="home-section getting-started" aria-labelledby="steps-title">
      <div class="section-heading"><div><span class="section-kicker">03 / 第一次使用</span><h2 id="steps-title">沿着这条路径，完成第一次比较</h2></div><span class="section-caption">点击步骤即可开始</span></div>
      <ol class="steps-grid"><li v-for="(step, index) in steps" :key="step.title"><button class="step-button" type="button" @click="step.action"><span class="step-number">0{{ index + 1 }}</span><span class="step-icon"><GuideIcon :name="step.icon" :size="26" /></span><strong>{{ step.title }}</strong><span class="step-description">{{ step.text }}</span><span class="step-arrow" aria-hidden="true">→</span></button></li></ol>
      <el-collapse v-model="detailsOpen" class="usage-details"><el-collapse-item title="查看录入与分析的操作说明" name="usage"><div class="usage-grid">
        <p><strong>实验和结果分开录入</strong>新建实验先保存模型和非空 JSON 参数；保存后，在实验详情中点击“录入结果”。也可以用“批量导入 JSON”录入多条实验。</p>
        <p><strong>从工作区进入比较</strong>勾选至少两个实验，点击“比较所选实验”。比较页可切换指标表格、可视化和 AI 总结；AI 总结需同项目至少两份有效结果，且存在共同指标，预览确认后手动生成。</p>
      </div></el-collapse-item></el-collapse>
    </section>
    <footer class="service-status" aria-label="后端服务状态"><div role="status" aria-live="polite" :aria-busy="state === 'loading'"><span class="status-dot" :class="state"></span>{{ state === 'loading' ? '正在连接服务' : state === 'healthy' ? '服务正常' : '后端服务不可用，请确认后端已启动' }}</div><el-button text :loading="state === 'loading'" :disabled="state === 'loading'" @click="checkHealth">重新检测</el-button></footer>
    <ProjectEntryPicker ref="picker" />
  </div>
</template>

<style scoped>
.home-content { color: #1e293b; }
.hero { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(220px, .8fr); gap: 40px; align-items: center; padding: 44px; border-radius: 20px; background: linear-gradient(115deg, #0f213b, #193f63); color: #fff; overflow: hidden; }
.eyebrow, .section-kicker { font-size: 11px; font-weight: 700; letter-spacing: 1.4px; }
.eyebrow { color: #9bc9f3; }
.hero h1 { font-size: clamp(30px, 3.4vw, 44px); line-height: 1.25; letter-spacing: -1px; margin: 16px 0; color: #fff; }
.hero-description { max-width: 560px; line-height: 1.85; color: #d3e1ee; font-size: 15px; margin: 0 0 24px; }
.hero-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.hero-actions .el-button { margin: 0; gap: 7px; }
.hero-actions .el-button--primary { background: #53d1bc; border-color: #53d1bc; color: #102c3c; font-weight: 700; }
.hero-actions .el-button--primary:hover { background: #85e2d2; border-color: #85e2d2; }
.hero-link { color: #dbeafe; text-decoration: none; padding: 10px 0; font-size: 14px; }
.hero-note { color: #a9c1d5; font-size: 12px; line-height: 1.7; margin: 20px 0 0; }
.hero-visual { border: 1px solid #ffffff26; background: #ffffff08; border-radius: 14px; padding: 24px; transform: rotate(-2deg); }
.visual-label { font-size: 12px; color: #c7dbea; display: flex; align-items: center; gap: 8px; }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: #65dbc0; }
.visual-bars { height: 115px; display: flex; align-items: flex-end; gap: 14px; padding: 20px 12px 0; border-bottom: 1px solid #ffffff30; }
.visual-bars span { flex: 1; background: #4b89b6; border-radius: 5px 5px 0 0; height: 38%; }
.visual-bars span:nth-child(2) { height: 61%; background: #67a8cf; }
.visual-bars span:nth-child(3) { height: 50%; }
.visual-bars span:nth-child(4) { height: 86%; background: #61d0b8; }
.visual-bars span:nth-child(5) { height: 72%; background: #88d8cc; }
.visual-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 16px; }
.visual-tags span { font-size: 10px; padding: 4px 7px; border-radius: 4px; background: #ffffff10; color: #cce1ef; }
.hero-visual p { font-size: 12px; color: #a9c1d5; margin: 14px 0 0; }
.home-section { margin-top: 40px; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
.section-kicker { color: #578092; }
.section-heading h2 { margin: 8px 0 0; font-size: 23px; letter-spacing: -.4px; }
.section-caption { color: #64748b; font-size: 12px; line-height: 1.6; }
.relationship-grid, .page-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
.relation-card { position: relative; min-width: 0; border: 1px solid #dce5ef; background: #fff; border-radius: 12px; padding: 22px; display: flex; flex-direction: column; }
.node-heading { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.icon-box { color: #356a9a; background: #eaf2fa; width: 42px; height: 42px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.node-en { font-size: 9px; letter-spacing: 1px; color: #64748b; }
.node-heading h3 { font-size: 17px; margin: 2px 0 0; }
.level-tag { margin-left: auto; color: #64748b; font-size: 10px; border: 1px solid #e2e8f0; border-radius: 4px; padding: 3px 5px; }
.node-description { font-size: 13px; color: #526479; line-height: 1.8; margin: 18px 0; }
.example-card, .experiment-example { padding: 16px; background: #f4f8fc; border: 1px solid #e2edf6; border-radius: 8px; }
.example-label { display: block; font-size: 11px; color: #64748b; margin-bottom: 8px; }
.example-card strong, .experiment-example strong { font-size: 14px; }
.metric-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.metric-pills span { background: #e3edf7; padding: 4px 8px; border-radius: 4px; color: #426280; font-size: 11px; }
.node-footnote { font-size: 11px; color: #64748b; line-height: 1.8; margin: auto 0 0; padding-top: 18px; }
.relation-connector { position: absolute; left: -29px; top: 60px; z-index: 1; padding: 4px 2px; background: #f6f8fb; color: #71859a; font-size: 10px; }
.batch-node .icon-box { background: #edf1fc; color: #6865b1; }
.experiment-node .icon-box { background: #e8f5f1; color: #27856d; }
.batch-example { display: flex; align-items: center; gap: 9px; padding: 13px; border: 1px solid #e4e7f3; background: #f7f8fd; border-radius: 7px; color: #6865b1; }
.batch-example strong { display: block; font-size: 13px; color: #3d4562; }
.batch-example span { display: block; font-size: 11px; margin-top: 4px; color: #64748b; }
.batch-example.secondary { margin-top: 9px; }
.experiment-example { background: #f3faf7; border-color: #dfede6; }
.experiment-example > div:first-child { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.config-tag { font-size: 10px; color: #39836d; background: #e0f1e9; padding: 3px 5px; border-radius: 4px; }
.experiment-example code { display: block; margin: 12px 0; font-size: 11px; color: #566b63; overflow-wrap: anywhere; }
.result-slot { display: flex; align-items: center; gap: 6px; padding-top: 12px; border-top: 1px dashed #c6ddd3; font-size: 12px; color: #33705b; }
.result-slot small { margin-left: auto; font-size: 10px; color: #64748b; }
.relationship-footer { display: flex; align-items: baseline; gap: 9px; font-size: 12px; line-height: 1.8; color: #526479; padding: 16px 0 0; }
.relationship-dot { width: 6px; height: 6px; flex: 0 0 6px; border-radius: 50%; background: #5f8eaa; }
.page-card { border: 1px solid #dce5ef; border-radius: 12px; background: #fff; padding: 24px; display: flex; flex-direction: column; min-width: 0; }
.page-card-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.page-card-heading > span:last-child { font-size: 11px; color: #64748b; }
.page-card h3 { margin: 20px 0 8px; font-size: 18px; }
.page-card p { margin: 0; color: #526479; line-height: 1.8; font-size: 13px; }
.page-card ul { padding: 0; margin: 18px 0 24px; list-style: none; }
.page-card li { display: flex; gap: 8px; color: #526479; font-size: 12px; line-height: 2.2; }
.page-card li > span { color: #3c917e; }
.page-card > a { color: #2563a4; font-size: 13px; font-weight: 600; text-decoration: none; display: flex; justify-content: space-between; border-top: 1px solid #edf1f5; padding-top: 16px; margin-top: auto; }
.getting-started { padding: 28px; border: 1px solid #dce5ef; border-radius: 14px; background: #fff; }
.steps-grid { list-style: none; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); padding: 0; margin: 26px 0 16px; gap: 12px; }
.step-button { position: relative; width: 100%; display: flex; flex-direction: column; align-items: flex-start; border: 1px solid transparent; background: #f6f8fb; border-radius: 9px; padding: 15px 12px; color: #31485e; font: inherit; text-align: left; cursor: pointer; min-height: 170px; }
.step-number { font-size: 10px; color: #71869a; font-weight: 600; letter-spacing: 1px; }
.step-icon { margin: 16px 0 12px; color: #447ba2; display: flex; }
.step-button strong { font-size: 13px; }
.step-description { font-size: 11px; line-height: 1.7; color: #64748b; margin-top: 6px; }
.step-arrow { position: absolute; right: -12px; top: 72px; z-index: 1; color: #71869a; }
.steps-grid li:last-child .step-arrow { display: none; }
.step-button:hover { border-color: #98b9d5; background: #edf5fc; }
.step-button:focus-visible, a:focus-visible { outline: 2px solid #2563a4; outline-offset: 4px; }
.usage-details { border: 0; }
.usage-details :deep(.el-collapse-item__header) { border: 0; font-size: 12px; color: #526479; }
.usage-details :deep(.el-collapse-item__wrap) { border: 0; }
.usage-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.usage-grid p { color: #64748b; font-size: 12px; line-height: 1.9; margin: 10px 0 0; }
.usage-grid strong { display: block; color: #334155; margin-bottom: 4px; }
.service-status { margin: 24px 0 0; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; color: #64748b; font-size: 12px; }
.service-status > div { display: flex; gap: 8px; align-items: center; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #94a3b8; flex-shrink: 0; }
.status-dot.healthy { background: #2fa286; }
.status-dot.unavailable { background: #df5a5a; }
@media (max-width: 1000px) { .hero { padding: 32px; gap: 24px; }
.relationship-grid, .page-grid { gap: 14px; }
.relation-card { padding: 18px; }
.level-tag { display: none; }
.relation-connector { left: -24px; }
.steps-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.steps-grid li:nth-child(3) .step-arrow { display: none; } }
@media (max-width: 700px) { .hero { grid-template-columns: minmax(0, 1fr); padding: 28px 24px; }
.hero-visual { display: none; }
.hero h1 { font-size: 34px; }
.relationship-grid, .page-grid { grid-template-columns: minmax(0, 1fr); gap: 16px; }
.relation-connector { left: auto; right: 18px; top: -18px; background: #f6f8fb; }
.relation-connector > span { display: inline-block; transform: rotate(90deg); }
.level-tag { display: inline; }
.section-heading h2 { font-size: 21px; }
.home-section { margin-top: 32px; }
.getting-started { padding: 20px; }
.steps-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.steps-grid li:nth-child(3) .step-arrow { display: inline; }
.steps-grid li:nth-child(even) .step-arrow { display: none; }
.usage-grid { grid-template-columns: minmax(0, 1fr); gap: 8px; } }
@media (prefers-reduced-motion: reduce) { .hero-visual { transform: none; } }
</style>
