<script setup>
import {computed, reactive, ref, watch} from 'vue';
import {DeleteOutlined, PlusOutlined} from '@ant-design/icons-vue';
import {message} from 'ant-design-vue';
import {get, post} from '@/utils/request.js'
// --- [核心修改] 从全局对象读取配置 ---
// 添加一个健壮性检查，如果配置文件加载失败，则提供一个空对象并报警
if (!window.APP_CONFIG) {
  alert('关键配置文件 external-config.js 加载失败！请检查 public/config/ 目录。');
  window.APP_CONFIG = {}; // 防止应用崩溃
}
const config = window.APP_CONFIG;
console.log('额外配置',config);
// 响应式状态
const taskContent = ref('');
const screenshot = ref(null);
const rawModelResponse = ref(null);
const modifiedResult = ref('');// 不再需要
const initLoading = ref(false);
const modelLoading = ref(false);
const taskTypes = [{ label: '购物', value: 'shopping' },{label:'消息',value:'chat'}];
const applications = {
  shopping: [{ label: '美团外卖', value: 'meituan_waimai' }],
  // 你可以继续添加其他类型和应用
  chat:[{label:'微信',value:'wechat'}]
};
const selectedTaskType = ref('shopping');
const selectedApplication = ref('meituan_waimai');
const shoppingTaskParameters = reactive({});
// 实现任务通用化
const taskParametersMap={
  // 购物任务的元数据定义
  shopping: {
    quantity: {
      label: '商品数量',
      type: 'number', // 'text', 'number', 'select' 等
      defaultValue: 1,
      props: { // 可以传递给组件的额外属性
        min: 1,
        style: 'width: 80px'
      }
    },
    item_name: {
      label: '商品名称',
      type: 'text',
      defaultValue: '',
      placeholder: '请输入商品名称'
    },
    store_name: {
      label: '店铺名称',
      type: 'text',
      defaultValue: '',
      placeholder: '请输入店铺名称'
    },
    specs: {
      label: '商品规格',
      type: 'text',
      defaultValue: '',
      placeholder: '（可选）如：大杯/去冰'
    }
  },
  chat: {
    test: {
      label: '测试参数',
      type: 'text',
      defaultValue: '',
      placeholder: '请输入测试参数'
    },
  }
}
// 当前展示的二级任务参数
const activeTaskParameters=reactive({});
// 【新增】计算属性，用于获取当前任务的表单“结构定义”
const activeTaskSchema = computed(() => {
  return taskParametersMap[selectedTaskType.value] || {};
});

// 使用 watch 监听任务类型的变化，来重置 activeTaskParameters
watch(selectedTaskType, (newType) => {
  const schema = taskParametersMap[newType];
  if (!schema) return;

  // 1. 清空旧的参数
  Object.keys(activeTaskParameters).forEach(key => delete activeTaskParameters[key]);

  // 2. 根据新的 schema 设置默认值
  for (const key in schema) {
    activeTaskParameters[key] = schema[key].defaultValue;
  }
}, { immediate: true }); // immediate: true 确保组件加载时立即执行一次
// --- [新增] 表单相关的状态和常量 ---
// Action 的所有可能类型
const actionTypes = config.actionTypes;
// app列表
// 主页通过home键解决
const appList = config.appList;

// Swipe 方向和距离的选项
const swipeDirections = [
  { label: '上', value: 'up' },
  { label: '下', value: 'down' },
  { label: '左', value: 'left' },
  { label: '右', value: 'right' },
];
const swipeDistances = [
  { label: '短', value: 'short' },
  { label: '中', value: 'medium' },
  { label: '长', value: 'long' },
];

// 用于驱动表单的响应式对象
// 废弃
const actionForm = reactive({
  action: null,
  x: null,
  y: null,
  value: '',
  direction: 'up',
  distance: 'medium',
  x_end: null,
  y_end: null,
  "app_value": ''
});
// 同一个轨迹的数据记录
const exampleStep={
  "step_index":1,
  "screenshot_64":"",
  "screenshot_xml":"",
  "actionForm":{},
  "extra_info":{
    "status":[
      {
        "content":"",
        "description":"",
      }
    ],
    "reasoning":"",
    "summary":"",
  }

}
// 工厂函数：返回一个新的步骤对象
// ===================================================================
// [核心修改 1] 重构 createStep 工厂函数
// ===================================================================
/**
 * 基于配置文件中的模板，创建一个全新的、独立的步骤对象。
 * @param {string} stepId - 要分配给新步骤的唯一ID。
 * @returns {object} 一个深拷贝后的新步骤对象。
 */
function createStep(stepId) {
  // 1. 使用 structuredClone 对模板进行深拷贝，确保所有嵌套对象都是新的
  const newStep = structuredClone(config.stepTemplate);

  // 2. 为新步骤设置唯一的 step_index
  newStep.step_index = stepId;

  // 3. 返回这个完全独立的新对象
  return newStep;
}
// 使用 createStep 函数来初始化 stepList，确保第一个步骤也是一个独立的深拷贝副本
let stepList = reactive([createStep('1')]);
const activeStepKey = ref("1");
// 不能更改计算属性本身，但可以修改其中的值
const activeStep = computed(() => {
  return stepList.find(step => step.step_index === activeStepKey.value) || null;
});
const instruction=ref('');// 用户指令描述
// 增加步骤
const addStep=()=>{
  const newId=crypto.randomUUID()
  stepList.push(createStep(newId));
  activeStepKey.value = newId;

}
const removeStep=targetKey=>{
  // 找到要删除的tab的索引
  const removedIndex = stepList.findIndex(step => step.step_index === targetKey);
  // console.log('removeKey',targetKey,removedIndex);
  if (removedIndex === -1) return;

  // 如果删除的是当前激活的tab，需要决定下一个激活哪个tab
  if (activeStepKey.value === targetKey) {
    const nextTab = stepList[removedIndex + 1] || stepList[removedIndex - 1];
    activeStepKey.value = nextTab ? nextTab.step_index : null;
    // console.log('activeStepKey',activeStepKey.value,activeStep.value);
  }

  // [正确做法] 使用 splice 直接修改原始响应式数组
  stepList.splice(removedIndex, 1);
};
// tabs组件的增加和删除监听函数
const onEdit = (targetKey, action) => {
  if (action === 'add') {
    addStep();
  } else {
    removeStep(targetKey);
  }
};
const allExtraInfoSchemas=config.allExtraInfoSchemas
const activeSchemaKey = ref(config.activeSchemaKey)
// 3. [核心] 创建一个计算属性，它会根据 activeSchemaKey 自动返回对应的 Schema 数组
const currentExtraInfoSchema = computed(() => {
  // 如果找不到对应的 schema，返回一个空数组以避免错误
  return allExtraInfoSchemas[activeSchemaKey.value] || [];
});
// 当用户切换模式时，清空当前步骤的 extra_info 是一个好习惯，以防止数据错乱
watch(activeSchemaKey, (newKey, oldKey) => {
  if (newKey !== oldKey && activeStep.value) {
    // 重置当前步骤的额外信息
    activeStep.value.extra_info = {};
    message.success(`已切换到 "${newKey}" 模式，额外信息已重置。`);
  }
});
const clearStepList=()=>{
  stepList.length=0;
  stepList.push(createStep('1'))
  activeStepKey.value='1';
  // 清空instruction
  instruction.value='';
}
/**
 * [新增] a-upload 上传前的处理函数
 * 将用户上传的图片文件转换为 Base64 字符串，并更新到 `screenshot` ref 中。
 * @param {File} file - 用户选择的文件对象
 * @returns {boolean} - 返回 false 以阻止 antd-vue 的默认上传行为
 */
const handleBeforeUpload = (file) => {
  // 1. 首先，立即获取当前激活的步骤对象
  const currentStep = activeStep.value;

  // 2. 添加一个安全检查，防止在没有激活步骤时上传
  if (!currentStep) {
    message.error('请先选择一个要上传截图的步骤！');
    return false; // 阻止上传
  }

  // 3. 创建 FileReader
  const reader = new FileReader();
  reader.readAsDataURL(file);

  // 4. 在 onload 回调中，直接修改我们之前获取到的那个响应式对象的属性
  reader.onload = () => {
    // 这行代码是关键！
    // currentStep 是对 stepList 中某个响应式对象的直接引用，
    // 修改它的属性会被 Vue 侦测到。
    currentStep.screenshot_64 = reader.result;

    message.success('本地图片加载成功！');
  };

  reader.onerror = () => {
    message.error('图片读取失败！');
  };

  // 5. 阻止 antd-vue 的默认上传行为
  return false;
};

/**
 * 将给定的图片URL转换为Base64编码的Data URL。
 *
 * @param {string} imageUrl 要转换的图片URL。
 * @returns {Promise<string>} 一个Promise，解析为Base64字符串（data:image/jpeg;base64,...），如果失败则reject。
 */
const convertImageToBase64 = (imageUrl) => {
  return new Promise(async (resolve, reject) => {
    try {
      // 1. 使用 fetch API 获取图片数据
      const response = await fetch(imageUrl);

      if (!response.ok) {
        // 如果HTTP请求不成功，抛出错误
        alert(`HTTP error! Status: ${response.status} for URL: ${imageUrl}`);
      }

      // 2. 获取 Blob 对象
      const imageBlob = await response.blob();

      // 3. 使用 FileReader 将 Blob 转换为 Base64
      const reader = new FileReader();

      reader.onloadend = () => {
        // FileReader 读取完成后，result 就是 Base64 格式的 Data URL
        resolve(reader.result);
      };

      reader.onerror = () => {
        // FileReader 发生错误时，reject Promise
        reject(new Error(`FileReader failed to read the image blob from ${imageUrl}.`));
      };

      reader.readAsDataURL(imageBlob); // 读取 Blob 为 Data URL (Base64)

    } catch (err) {
      // 捕获 fetch 或其他异步操作中的错误，并 reject Promise
      reject(new Error(`Failed to fetch or process image "${imageUrl}": ${err.message}`));
    }
  });
};
// 初始化app
const initApp= async ()=>{
  await post('/restart-app');

  // 定义要等待的时间（毫秒）
  const delay = 5000; // 5秒
// 使用 setTimeout 进行延时执行
  setTimeout(() => {
    // 在这里放置你希望延迟执行的代码
    getScreenshot()
  }, delay);

  // 加载截图-adb未成功前的临时处理
  // console.log(screenshot_base64);
  // screenshot.value = await convertImageToBase64('src/assets/screenshots/01_main_page.png');
}
const testImageLoad=async ()=>{
  screenshot.value = await convertImageToBase64('src/assets/screenshots/01_main_page.png');
}
/**
 * [新增] 一个辅助函数，用于根据后端返回的 action 对象更新表单
 * @param {object} actionObject - 从后端获取的 action JSON 对象
 */
const updateActionForm = (actionObject) => {
  if (!actionObject || !actionObject.action) {
    // 如果没有数据，重置表单
    actionForm.action = null;
    actionForm.x = null;
    actionForm.y = null;
    actionForm.value = '';
    actionForm.direction = 'up';
    actionForm.distance = 'medium';
    actionForm.x_end = null;
    actionForm.y_end = null;
    return;
  }
  // 使用 Object.assign 来填充表单，后端返回的对象可能不包含所有字段
  // 后面属性的优先级更高
  Object.assign(actionForm, {
    // 先设置默认值
    action: null,
    x: null,
    y: null,
    value: '',
    direction: 'up',
    distance: 'medium',
    x_end: null,
    y_end: null,
    // 再用后端数据覆盖
    ...actionObject
  });
};
// --- [新增] 用于存储鼠标在图片上坐标的状态 ---
const mouseCoordinates = ref({ x: 0, y: 0 });
// [新增] 用于存储图片原始分辨率的状态
const originalImageSize = ref({ width: 0, height: 0 });
const showImageSize = ref({ width: 0, height: 0 });// 显示的图片尺寸
// [新增] 用于获取截图包裹容器DOM元素的模板引用
const screenshotWrapperRef = ref(null);
// --- [新增] Canvas 的模板引用 ---
const canvasRef = ref(null);
const user_id = ref('');// 用户id,用于将标注保存到不同的标注中
/**
 * [重构] 核心绘图函数：重绘基础截图
 * 负责清空Canvas并绘制当前的截图。这是所有预览和重置操作的基础。
 */
// TODO: 上传横版图片会有问题
const redrawBaseImage = () => {
  const canvas = canvasRef.value;
  // 如果 canvas 元素还没有被挂载，就直接退出函数。
  if (!canvas) {
    return;
  }


  // [修复 1] 使用正确的数据源
  const src = activeStep.value ? activeStep.value.screenshot_64 : null;
  // console.log(!canvas);
  const ctx = canvas.getContext('2d');

  // 如果没有截图，则清空画布
  if (!src) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    originalImageSize.value = { width: 0, height: 0 };
    return;
  }

  const img = new Image();
  img.onload = () => {
    // [修复 2] 移除 if 判断，每次都重新计算尺寸，使函数更健壮
    originalImageSize.value = { width: img.width, height: img.height };

    const dpr = window.devicePixelRatio || 1;
    const displayHeight = canvas.clientHeight;
    const displayWidth = displayHeight * img.width / img.height;

    // 设置物理像素尺寸，以保证高清
    canvas.width = displayWidth * dpr;
    canvas.height = displayHeight * dpr;

    // 缩放上下文，使得后续绘图可以使用逻辑像素（CSS像素）单位
    // 注意：每次重设 canvas.width/height 都会重置 context 的状态，所以 scale 不会累积
    ctx.scale(dpr, dpr);
    ctx.imageSmoothingEnabled = true; // 可选，提升图片缩放质量
    ctx.imageSmoothingQuality = 'high';

    // 执行绘图 (使用逻辑像素尺寸)
    ctx.clearRect(0, 0, displayWidth, displayHeight);
    ctx.drawImage(img, 0, 0, displayWidth, displayHeight);
  };
  img.onerror = () => console.error("无法加载图片用于绘制。");
  img.src = src;
};
/**
 * [核心] 监听当前激活步骤的 screenshot_64 属性。
 * 当它发生变化时（例如：用户截图、切换Tab、上传图片），自动调用 redrawBaseImage。
 */
watch(() => activeStep.value?.screenshot_64, (newScreenshot, oldScreenshot) => {
  // 当 activeStep.value.screenshot_64 变化时，这个回调函数就会执行

  // 可以在这里加一个日志，方便调试
  // if (newScreenshot) {
  //   console.log('当前步骤的截图已更新，准备重绘 Canvas。');
  // } else {
  //   console.log('当前步骤没有截图，准备清空 Canvas。');
  // }
  console.log(stepList);

  // 调用你已经写好的绘图函数
  redrawBaseImage();
}, {
  // immediate: true 是一个非常有用的选项，它会确保：
  // 1. 组件加载后，立即执行一次 watch 回调，绘制初始状态的 Canvas。
  // 2. 如果不加，只有在 screenshot_64 第一次“变化”后才会绘制。
  immediate: true
});




// 推理
const infer=async ()=>{
  // const res= await post('/infer',{
  //   'image_base64': screenshot.value,
  //   'slot_info': {
  //     'task_type':selectedTaskType.value,
  //     'app_name':selectedApplication.value,
  //     'quantity':shoppingTaskParameters.count,
  //     'item_name':shoppingTaskParameters.product_name,
  //     'store_name':shoppingTaskParameters.store_name,
  //     'specs':shoppingTaskParameters.specifications
  //   }
  // });
  const res= await post('/infer',{
    'image_base64': screenshot.value,
    'task_type':selectedTaskType.value,
    'app_name':selectedApplication.value,
    'slot_info': {
      ...activeTaskParameters
    }
  });
  if(res.status==='success'){
    console.log('模型响应',res.data);
    rawModelResponse.value = res.data; // 保存原始响应
    updateActionForm(res.data); // 使用新函数更新我们的表单
    // 预览标注
    handlePreview();
  }
}
// multi-agents推理
const infer_multi_agents=async ()=>{
  const res= await post('/infer_multi_agents',{
    'image_base64': screenshot.value,
    'task_type':selectedTaskType.value,
    'app_name':selectedApplication.value,
    'slot_info': {
      ...activeTaskParameters
    }
  });
  console.log('multi-agent推理',res)
  if(res.status==='success'){
    console.log('模型响应',res.data);
    rawModelResponse.value = res.data; // 保存原始响应
    updateActionForm(res.data); // 使用新函数更新我们的表单
    // 预览标注
    handlePreview();
  }
}
// 获取截图
const getScreenshot=async ()=>{
  try {
    const res= await get('/get-screenshot');
    if(res.status === 'success'){
      const screenshot_base64=res.data;
      console.log(screenshot_base64);
      activeStep.value.screenshot_64=screenshot_base64;
    }
  }catch(err){
    alert(err);
  }
}
// 获取xml树
const getXML=async ()=>{
  try {
    const res= await get('/get-ally');
    if(res.status === 'success'){
      const ui_xml=res.data;
      console.log('xml',ui_xml);

    }
  }catch(err){
    alert(err);
  }
}
// 获取截图、xml树、前台包名
const packageName=ref('')
const getAll=async ()=>{
  try {
    const res= await get('/get-all');
    if(res.status === 'success'){
      const data=res.data;
      activeStep.value.screenshot_64=data["screenshot_base64"];
      activeStep.value.screenshot_xml=data["ui_xml"];
      packageName.value=data["package"];
      console.log('all',data);
    }
  }catch(err){
    alert(err);
  }
}
// 生成任务
const generateTask = () => {
  // shoppingTaskParameters.count=2;
  // shoppingTaskParameters.product_name='多肉葡萄';
  // shoppingTaskParameters.store_name='喜茶';
  // shoppingTaskParameters.specifications='';
  console.log('生成任务');
}
const handleSaveAnnotationOnly = async () => {
  try {
    await post('/save-annotation', {
      'image_base64': screenshot.value,
      'task_type':selectedTaskType.value,
      'app_name':selectedApplication.value,
      'slot_info': {
        ...activeTaskParameters
      },
      'action_info':actionForm,
      'user_id':user_id.value,

    });
    console.log(actionForm.value);
    message.success('标注保存成功');
    // 清空标注
    // Object.assign(actionForm, {
    //   // 设置默认值
    //   action: null,
    //   x: null,
    //   y: null,
    //   value: '',
    //   direction: 'up',
    //   distance: 'medium',
    //   x_end: null,
    //   y_end: null,
    // });
    // 获取应用截图
    // await getScreenshot();
    // 清空过时的ActionForm

  } catch (error) {
    message.error(`保存失败: ${error.message}`);
  }
  // message.success('标注保存成功');
  // screenshot.value=await convertImageToBase64('src/assets/screenshots/02_search_store.png');
};

// 保存标注
const handleSaveAnnotation = async () => {
  try {
    await post('/save-annotation', {
      'image_base64': screenshot.value,
      'task_type':selectedTaskType.value,
      'app_name':selectedApplication.value,
      'slot_info': {
        ...activeTaskParameters
      },
      'action_info':actionForm,
      'user_id':user_id.value,

    });
    console.log(actionForm.value);
    // 执行真实操作
    await post('/execute-action', {
      action_info: actionForm
    });
    message.success('标注保存成功');
    // 清空标注
    Object.assign(actionForm, {
      // 设置默认值
      action: null,
      x: null,
      y: null,
      value: '',
      direction: 'up',
      distance: 'medium',
      x_end: null,
      y_end: null,
    });
    // 获取应用截图
    // await getScreenshot();
    // 清空过时的ActionForm

    // 获取应用截图
    setTimeout(()=>{
      getScreenshot();
    },1000)
  } catch (error) {
    message.error(`保存失败: ${error.message}`);
  }
  // message.success('标注保存成功');
  // screenshot.value=await convertImageToBase64('src/assets/screenshots/02_search_store.png');
};
// 仅保存标注
const handleSaveAnnotationOnlyNew = async () => {
  try {
    console.log('保存标注',stepList)
    await post('/save-annotation-new', {
      'user_id':user_id.value,
      'step_list':stepList,
      'instruction':instruction.value
    });
    message.success('标注保存成功');

  } catch (error) {
    message.error(`保存失败: ${error.message}`);
  }
  // message.success('标注保存成功');
  // screenshot.value=await convertImageToBase64('src/assets/screenshots/02_search_store.png');
};
// 单步执行任务
const executeStep=async ()=>{
  console.log('actionForm',activeStep.value.actionForm)
  if(activeStep.value.actionForm.action==='open_app'){
    const app_value=activeStep.value.actionForm.app_value;
    activeStep.value.actionForm.package_name=config.packageList[app_value];
  }

  await post('/execute-action', {
    action_info: activeStep.value.actionForm
  });
  message.success('执行成功');
  // 增加新tab，加载截图
  // 获取应用截图
  setTimeout(()=>{
    addStep()
    getAll()
  },1000)

}
/**
 * [新增] 封装后的坐标换算函数 (纯函数)
 * 将鼠标在元素上的显示坐标转换为相对于图片原始分辨率的真实坐标。
 *
 *  @param {number} mouseX 鼠标在 Canvas 元素上的 X 坐标（显示坐标）。
 *  @param {number} mouseY 鼠标在 Canvas 元素上的 Y 坐标（显示坐标）。
 * @returns {{x: number, y: number} | null} - 返回计算后的真实坐标对象，如果无法计算则返回 null。
 */
/**
 * [优化] 坐标转换：将显示坐标转换为真实坐标 (修复了计算bug)
 */
const convertDisplayCoordsToReal = (mouseX, mouseY) => {
  const canvas = canvasRef.value;
  if (!canvas || !originalImageSize.value.width) return null;

  const displayW = canvas.clientWidth;
  const displayH = canvas.clientHeight;
  const originalW = originalImageSize.value.width;
  const originalH = originalImageSize.value.height;

  if (displayW === 0 || displayH === 0) return null;

  const realX = Math.round((mouseX / displayW) * originalW);
  const realY = Math.round((mouseY / displayH) * originalH);

  return { x: realX, y: realY };
};

// --- [新增] 鼠标在截图上移动的事件处理函数 ---
/**
 * 处理鼠标在截图图片上移动的事件。
 * @param {MouseEvent} event - 鼠标事件对象
 */
const handleScreenshotMousemove = (event) => {
  // event.offsetX 和 event.offsetY 能直接获取鼠标相对于事件源元素（这里是图片）左上角的坐标
  // 调用封装好的函数进行计算
  // 更新状态
  mouseCoordinates.value = convertDisplayCoordsToReal(
      event.offsetX,
      event.offsetY,
  );
};

/**
 * [新增] 当鼠标移出图片区域时，重置坐标显示
 */
const handleScreenshotMouseleave = () => {
  mouseCoordinates.value = { x: 0, y: 0 }; // 或者重置为 { x: 0, y: 0 }，设为null可以隐藏显示
}
/**
 * [新增] 点击 Canvas 时，自动填充坐标到表单中。
 * 这是一个非常实用的交互增强。
 */
const handleCanvasClick = (event) => {
  if (activeStep.value.actionForm.action === 'tap' || activeStep.value.actionForm.action === 'long_press' || activeStep.value.actionForm.action === 'swipe') {
    // 之前这里传递的参数不正确，已修复
    const coords = convertDisplayCoordsToReal(
        event.offsetX,
        event.offsetY
    );
    if (coords) {
      activeStep.value.actionForm.x = coords.x;
      activeStep.value.actionForm.y = coords.y;
      message.success(`坐标已更新: (${coords.x}, ${coords.y})`);
      // 更新标注
      handlePreview();
    }
  }if(activeStep.value.actionForm.action === 'swipe_two_points' ) {
    const coords = convertDisplayCoordsToReal(
        event.offsetX,
        event.offsetY
    );
    // 如果初始坐标存在则填充初始坐标
    if(!activeStep.value.actionForm.x||!activeStep.value.actionForm.y){
      if(coords) {
        activeStep.value.actionForm.x = coords.x;
        activeStep.value.actionForm.y = coords.y;
        message.success(`起始坐标已更新: (${coords.x}, ${coords.y})`);
      }
    }else{
      // 填充末尾坐标
      // 相对距离长的轴决定方向,另一个轴决定距离
      const x_distance = Math.abs(coords.x - activeStep.value.actionForm.x);
      const y_distance = Math.abs(coords.y - activeStep.value.actionForm.y);
      if(x_distance >= y_distance){
        activeStep.value.actionForm.x_end = coords.x;
        activeStep.value.actionForm.y_end = activeStep.value.actionForm.y;
      }else{
        activeStep.value.actionForm.x_end = activeStep.value.actionForm.x;
        activeStep.value.actionForm.y_end = coords.y;
      }
      message.success(`末尾坐标已更新: (${activeStep.value.actionForm.x_end}, ${activeStep.value.actionForm.y_end})`);
      handlePreview();
    }
  }
};
/**
 * [新增] 预览操作处理函数
 * 这是“预览操作”按钮的核心逻辑。
 */
const handlePreview = () => {
  const action = activeStep.value.actionForm.action;
  const screenshot = activeStep.value.screenshot_64;
  if (! screenshot|| !action) {
    message.warn('请先加载截图并生成一个操作');
    return;
  }

  // 1. 先重绘基础图片，清除旧的预览
  redrawBaseImage();

  const canvas = canvasRef.value;
  // 等待图片绘制完成后再画标注
  setTimeout(() => {
    const ctx = canvas.getContext('2d');

    // 2. 根据操作类型绘制标注
    if (action === 'tap' || action === 'long_press') {
      if (activeStep.value.actionForm.x == null || activeStep.value.actionForm.y == null) {
        message.warn('预览失败：坐标不完整');
        return;
      }
      const displayCoords = convertRealCoordsToDisplay(activeStep.value.actionForm.x, activeStep.value.actionForm.y);
      if (displayCoords) {
        drawTapOnCanvas(ctx, displayCoords.x, displayCoords.y);
      }
    } else if (action === 'swipe') {
      if (activeStep.value.actionForm.x == null || activeStep.value.actionForm.y == null) {
        message.warn('预览失败：起始坐标不完整');
        return;
      }
      const startCoords = convertRealCoordsToDisplay(activeStep.value.actionForm.x, activeStep.value.actionForm.y);
      if (startCoords) {
        // 定义不同距离在屏幕上的像素长度
        const distanceMap = { short: 80, medium: 150, long: 220 };
        const length = distanceMap[activeStep.value.actionForm.distance] || 150;

        let endX = startCoords.x;
        let endY = startCoords.y;

        switch (activeStep.value.actionForm.direction) {
          case 'up':    endY -= length; break;
          case 'down':  endY += length; break;
          case 'left':  endX -= length; break;
          case 'right': endX += length; break;
        }
        drawTapOnCanvas(ctx, startCoords.x, startCoords.y);
        drawSwipeArrowOnCanvas(ctx, startCoords.x, startCoords.y, endX, endY);
      }
    } else if (action === 'swipe_two_points') {
      if (activeStep.value.actionForm.x == null || activeStep.value.actionForm.y == null) {
        message.warn('预览失败：起始坐标不完整');
        return;
      }
      if(activeStep.value.actionForm.x_end == null || activeStep.value.actionForm.y_end == null) {
        message.warn('预览失败: 终止坐标不完整');
        return;
      }
      const startCoords = convertRealCoordsToDisplay(activeStep.value.actionForm.x, activeStep.value.actionForm.y);
      const endCoords = convertRealCoordsToDisplay(activeStep.value.actionForm.x_end, activeStep.value.actionForm.y_end);
      if (startCoords&&endCoords) {
        drawTapOnCanvas(ctx, startCoords.x, startCoords.y);
        drawSwipeArrowOnCanvas(ctx, startCoords.x, startCoords.y, endCoords.x, endCoords.y);
      }
    } else {
      message.info('该操作类型不支持预览');
    }
  }, 100); // 短暂延迟确保图片已绘完
};

/**
 * [新增] 绘图工具：在Canvas上画十字圆环
 */
const drawTapOnCanvas = (ctx, x, y) => {
  ctx.beginPath();
  ctx.strokeStyle = '#FF4D4F'; // 使用醒目的红色
  ctx.lineWidth = 1.5;

  // 画圆
  const radius = 10;
  ctx.arc(x, y, radius, 0, 2 * Math.PI);

  // 画十字
  ctx.moveTo(x - radius - 8, y);
  ctx.lineTo(x + radius + 8, y);
  ctx.moveTo(x, y - radius - 8);
  ctx.lineTo(x, y + radius + 8);

  ctx.stroke();
};

/**
 * [新增] 绘图工具：在Canvas上画箭头
 */
const drawSwipeArrowOnCanvas = (ctx, fromX, fromY, toX, toY) => {
  ctx.beginPath();
  ctx.strokeStyle = '#110a01'; // 使用醒目的绿色
  ctx.fillStyle = '#0c0c0b';
  ctx.lineWidth = 2;

  // 画线
  ctx.moveTo(fromX, fromY);
  ctx.lineTo(toX, toY);

  // 画箭头
  const headlen = 15; // 箭头头的长度
  const angle = Math.atan2(toY - fromY, toX - fromX);

  ctx.moveTo(toX, toY);
  ctx.lineTo(toX - headlen * Math.cos(angle - Math.PI / 6), toY - headlen * Math.sin(angle - Math.PI / 6));
  ctx.moveTo(toX, toY);
  ctx.lineTo(toX - headlen * Math.cos(angle + Math.PI / 6), toY - headlen * Math.sin(angle + Math.PI / 6));

  ctx.stroke();
};


/**
 * [新增] 坐标转换：将真实坐标转换为Canvas显示坐标
 */
const convertRealCoordsToDisplay = (realX, realY) => {
  const canvas = canvasRef.value;
  if (!canvas || !originalImageSize.value.width) return null;

  const displayW = canvas.clientWidth;
  const displayH = canvas.clientHeight;
  const originalW = originalImageSize.value.width;
  const originalH = originalImageSize.value.height;

  const displayX = (realX / originalW) * displayW;
  const displayY = (realY / originalH) * displayH;

  return { x: displayX, y: displayY };
};
// 重置修改
const handleReset = () => {
  updateActionForm(rawModelResponse.value);
  redrawBaseImage(); // 清除画布上的所有预览标注
  message.info('已重置为原始推理结果');
};
// 测试截图
const testRestart= async ()=>{
  try {
    const res = await post('/restart-app');
    if(res.status === 'status'){
      message.success('成功重启')
    }
  }catch(error){
    console.error(error);
  }


}
// 生成llm
const llm_generate_task=async ()=>{
  try {
    const prompt = [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "请生成符合以下条件的 Android 复杂 GUI 长链任务数据：\n" +
                "1. 步骤不少于 20 步，且步骤之间有状态依赖。\n" +
                "2. 涉及单个或多个 Android 应用。\n" +
                "3. 用户目标以自然语言描述，隐含复杂逻辑。\n" +
                "4. 至少包含 3 个明确的“里程碑”节点（成功登录、完成关键搜索、提交表单、保存文件等）。\n" +
                "5. 任务中可能遇到干扰（如弹窗广告、网络延时、UI变动）。\n" +
                "6. 输出为纯json，请直接输出 JSON，不要包含任何 Markdown 代码块、解释文字或额外符号，不要加 ```json,格式如下：\n" +
                "{\n" +
                "  \"task_id\": \"唯一ID\",\n" +
                "  \"user_goal\": \"自然语言描述的任务目标\",\n" +
                "  \"apps_involved\": [\"App1\", \"App2\", ...],\n" +
                "  \"step_outline\": [\"Step1\", \"Step2\", ... 至少20步],\n" +
                "  \"milestones\": [\"Milestone1\", \"Milestone2\", \"Milestone3\"],\n" +
                "  \"possible_interruptions\": [\"干扰1\", \"干扰2\"]\n" +
                "}"
          }
        ]
      }
    ]
    const res = await post('/openai_infer',{
      'prompt_json':prompt,
    });

    if(res.status === 'success'){
      message.success('成功生成任务');
      console.log("生成的任务",res.data);
    }
  }catch(error){
    console.error(error);
  }
}
function buildLLMInferPrompt(previousSteps, currentScreenshot, taskType, appName) {
  const actionTypes = [
    'tap', 'text', 'need_feedback', 'long_press', 'swipe',
    'swipe_two_points', 'wait', 'FINISH', 'open_app'
  ];

  // 里程碑锚点说明（长链任务背景）
  const milestoneDescription = `
长链任务是在移动端（如 Android）中执行的一类复杂操作流程，通常包含十几到几十个相互依赖的步骤，跨多个界面甚至多个应用。
后续步骤的正确性严重依赖前面关键操作的结果。任何早期的小失误都可能在后面放大成任务失败，
而单靠当下屏幕的信息往往无法推断正确的下一步。

为提高执行稳定性，我们引入了“里程碑锚点”（关键步信息）：
- 它是一种从历史操作中提取的稀疏、高价值的结构化线索。
- 用来标记任务里的关键节点（如“成功登录账户”“成功提交搜索”“商品已加入购物车”）。
- 为后续步骤提供必要的上下文约束，并帮助智能体理解每一阶段的意义。
- 在遇到干扰或上下文丢失时，能够更准确地恢复状态并继续执行任务。
`;

  return `
你是一个智能任务标注助手。根据此前步骤的信息和当前的 Android 界面截图，推断当前步骤的操作 (action) 以及额外信息 (extra_info)。
必须严格遵守以下输出格式，并用 JSON 表示，不能添加任何解释文字，不能添加任何markdown格式的内容。

任务类型: ${taskType}
应用: ${appName}

此前步骤信息(JSON):
${JSON.stringify(previousSteps, null, 2)}

当前截图(base64):
${currentScreenshot}

里程碑锚点说明:
${milestoneDescription}

# 输出格式要求：
{
  "action": {
    "action": <string 或 null, 必须是以下之一: ${actionTypes.join(', ')}>,
    "x": <number 或 null>,
    "y": <number 或 null>,
    "value": "<string>",
    "direction": "up" 或 "down" 或 "left" 或 "right",
    "distance": "short" 或 "medium" 或 "long",
    "x_end": <number 或 null>,
    "y_end": <number 或 null>,
    "app_value": "<string>"
  },
  "extra_info": {
    "status": [
      {
        "content": "<里程碑锚点的内容>",
        "description": "<对这个里程碑锚点的描述>"
      }
    ],
    "reasoning": "<当前这步的推理结果>",
    "summary": "<这步的总结>"
  }
}

注意：
1. 所有 key 都必须出现，即使值为 null 或空字符串。
2. action.action 的值必须严格来自提供的类型列表。
3. 不要输出除 JSON 外的任何文字或解释。
  `;
}

const llm_infer = async () => {
  if (!activeStep.value?.screenshot_64) {
    message.warning('当前步骤缺少截图');
    return;
  }

  const previousStepsInfo = stepList
      .filter(s => s.step_index !== activeStep.value.step_index)
      .map(s => ({
        step_index: s.step_index,
        action: s.actionForm,
        extra_info: s.extra_info
      }));

  const prompt = buildLLMInferPrompt(
      previousStepsInfo,
      activeStep.value.screenshot_64,
      selectedTaskType.value,
      selectedApplication.value
  );
  const messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": prompt
        }
      ]
    }
  ]

  try {
    message.loading({ content: 'LLM 推理中...', key: 'llm' });
    const res = await post('/openai_infer', {
      'prompt_json':messages,
    });
    message.destroy('llm');

    if (res.status==='success' && res.data) {
      let parsed=res.data
      console.log('辅助更新',res.data)

      if (parsed.action) updateActionForm(parsed.action);
      if (parsed.extra_info) activeStep.value.extra_info = parsed.extra_info;
      message.success('LLM 辅助标注已更新');
    } else {
      message.error(res.message || 'LLM 推理失败');
    }
  } catch (err) {
    message.destroy('llm');
    message.error('LLM 推理接口调用失败');
    console.error(err);
  }
};
/**
 * [增强版] 为动态列表添加一个新项
 * @param {string} listKey - 要操作的列表的键名 (e.g., 'status')
 * @param {Array} itemSchema - 该列表项的 schema，用于生成空对象
 */
const addListItem = (listKey, itemSchema) => {
  if (!activeStep.value.extra_info[listKey]) {
    activeStep.value.extra_info[listKey] = [];
  }

  // 动态地根据 itemSchema 创建一个新的空对象
  const newItem = {};
  itemSchema.forEach(field => {
    // 根据字段类型赋予合适的初始值，这里简单处理为 null
    newItem[field.key] = null;
  });

  activeStep.value.extra_info[listKey].push(newItem);
};

/**
 * 从动态列表中移除一个项 (这个函数无需改变)
 * @param {string} listKey - 要操作的列表的键名 (e.g., 'status')
 * @param {number} index - 要移除的项的索引
 */
const removeListItem = (listKey, index) => {
  activeStep.value.extra_info[listKey].splice(index, 1);
};

</script>

<template>
  <a-layout class="container">
    <!-- 在任务输入区部分加入（可以在按钮旁边） -->
    <a-space style="margin-bottom: 16px;">
      用户id:
      <a-input  v-model:value="user_id" ></a-input>
      任务描述：
      <a-input v-model:value="instruction"></a-input>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="llm_generate_task"
          disabled
      >
        生成任务
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="initApp"
          v-if="false"
      >
        重启app,截图
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="llm_infer"
          disabled
      >
        请求模型,生成操作
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="infer_multi_agents"
          v-if="false"
      >
        multi-agents请求
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="handleSaveAnnotation"
          v-if="false"
      >
        保存结果,执行,截图
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="getAll"
      >
        截图
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="handleSaveAnnotationOnlyNew"
      >
        保存标注
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="testImageLoad"
          v-if="false"
      >
        测试截图
      </a-button>
      <a-button
          type="primary"
          :loading="initLoading"
          @click="testRestart"
          v-if="false"
      >
        测试重启app
      </a-button>
      <!-- [新增] 本地图片上传功能 -->
      <a-upload
          :before-upload="handleBeforeUpload"
          :show-upload-list="false"
      >
        <a-button type="primary">
          上传本地图片
        </a-button>
      </a-upload>
      <a-button @click="getXML" v-if="false">获取xml</a-button>
      <a-button @click="clearStepList">清空</a-button>
<!--      <a-button @click="getAll">三合一</a-button>-->
      当前包名：{{packageName}}
    </a-space>


    <!-- 参数输入部分 - 完全动态化 -->
    <!-- 主要内容区 -->
<!--    {{activeStep}}-->
    <a-tabs
      v-model:activeKey="activeStepKey"
      type="editable-card"
      @edit="onEdit"
    >
      <template #leftExtra>
<!--        <a-button @click="addStep">新建步骤</a-button>-->
        任务链--->
      </template>
      <a-tab-pane
        v-for="(step,index) in stepList"
        :key="step.step_index"
        :tab="`step ${index}`"
        :closable="step.step_index !== '1'"
      >

      </a-tab-pane>

    </a-tabs>
    <a-layout-content class="content">
      <a-row :gutter="24">
        <!-- 截图展示列 -->
        <a-col :span="12">
          <a-card title="应用截图" >
            <!-- [修改] 在卡片标题区域添加坐标显示 -->
            <template #extra>
              <span v-if="originalImageSize">
                原始分辨率: ({{ originalImageSize.width }}, {{ originalImageSize.height }})
              </span>
              <span v-if="mouseCoordinates">
                坐标: ({{ mouseCoordinates.x }}, {{ mouseCoordinates.y }})
              </span>
            </template>
            <!--
              [核心修改]
              将事件监听器从 a-image 移到这个 div 上。
              这个 div 是我们自己控制的，事件绑定更可靠。
            -->
            <div
                class="screenshot-wrapper"
                ref="screenshotWrapperRef"
            >
              <canvas
                  ref="canvasRef"
                  class="screenshot-img"
                  v-show="activeStep.screenshot_64"
                  @mousemove="handleScreenshotMousemove"
                  @mouseleave="handleScreenshotMouseleave"
                  @click="handleCanvasClick"
              ></canvas>

              <a-empty v-if="!activeStep.screenshot_64" description="请先获取截图" />
            </div>
          </a-card>
        </a-col>

        <!-- 标注编辑列 -->
        <a-col :span="12">
          <a-card title="标注界面">
            <a-skeleton :loading="modelLoading">
              <!-- 如果没有模型响应，显示提示信息 -->
              <a-empty v-if="!activeStep.screenshot_64" description="等待图片加载..." />

              <!-- [修改] 使用结构化表单替代文本域 -->
              <div v-else>
<!--                {{activeStep.actionForm}}-->
                <a-form  layout="vertical" :model="activeStep.actionForm" class="annotation-editor">
                  <!-- Action Type 下拉框 -->
                  <a-form-item label="操作类型 (Action)">
                    <a-select
                        v-model:value="activeStep.actionForm.action"
                        :options="actionTypes"
                        placeholder="请选择操作类型"
                    />
                  </a-form-item>

                  <!-- 条件渲染: tap 或 long_press -->
                  <a-space v-if="activeStep.actionForm.action === 'tap' || activeStep.actionForm.action === 'long_press'">
                    <a-form-item label="坐标 X">
                      <a-input-number v-model:value="activeStep.actionForm.x" placeholder="X" />
                    </a-form-item>
                    <a-form-item label="坐标 Y">
                      <a-input-number v-model:value="activeStep.actionForm.y" placeholder="Y" />
                    </a-form-item>
                  </a-space>

                  <!-- 条件渲染: text -->
                  <a-form-item label="输入内容" v-if="activeStep.actionForm.action === 'text'">
                    <a-input v-model:value="activeStep.actionForm.value" placeholder="请输入文本" />
                  </a-form-item>

                  <!-- 条件渲染: need_feedback -->
                  <a-form-item label="输入需要反馈给用户的内容" v-if="activeStep.actionForm.action === 'need_feedback'">
                    <a-input v-model:value="activeStep.actionForm.value" placeholder="请输入文本" />
                  </a-form-item>

                  <!-- 条件渲染: swipe -->
                  <template v-if="activeStep.actionForm.action === 'swipe'">
                    <a-space>
                      <a-form-item label="起始坐标 X">
                        <a-input-number v-model:value="activeStep.actionForm.x" placeholder="X" />
                      </a-form-item>
                      <a-form-item label="起始坐标 Y">
                        <a-input-number v-model:value="activeStep.actionForm.y" placeholder="Y" />
                      </a-form-item>
                    </a-space>
                    <a-space>
                      <a-form-item label="滑动方向">
                        <a-select
                            v-model:value="activeStep.actionForm.direction"
                            :options="swipeDirections"
                            style="width: 120px"
                        />
                      </a-form-item>
                      <a-form-item label="滑动距离">
                        <a-select
                            v-model:value="activeStep.actionForm.distance"
                            :options="swipeDistances"
                            style="width: 120px"
                        />
                      </a-form-item>
                    </a-space>
                  </template>
                  <!-- 条件渲染: swipe_two_points -->
                  <template v-if="activeStep.actionForm.action === 'swipe_two_points'">
                    <a-space>
                      <a-form-item label="起始坐标 X">
                        <a-input-number v-model:value="activeStep.actionForm.x" placeholder="X" />
                      </a-form-item>
                      <a-form-item label="起始坐标 Y">
                        <a-input-number v-model:value="activeStep.actionForm.y" placeholder="Y" />
                      </a-form-item>
                    </a-space>
                    <a-space>
                      <a-form-item label="终止坐标 X">
                        <a-input-number v-model:value="activeStep.actionForm.x_end" placeholder="X" />
                      </a-form-item>
                      <a-form-item label="终止坐标 Y">
                        <a-input-number v-model:value="activeStep.actionForm.y_end" placeholder="Y" />
                      </a-form-item>
                    </a-space>
                  </template>
                  <!-- wait 和 FINISH 不需要额外输入框 -->
                  <!-- 条件渲染: open_app -->
                  <a-form-item label="选择应用包名" v-if="activeStep.actionForm.action === 'open_app'">
                    <a-select
                        v-model:value="activeStep.actionForm.app_value"
                        placeholder="请选择要打开的应用"
                        :options="appList"
                        style="width:220px"
                    >
                    </a-select>
                  </a-form-item>

                  <a-divider />
                  <div class="action-bar">
                    <a-button @click="handlePreview" :disabled="!activeStep.actionForm.action">预览操作</a-button>
                    <a-button
                        type="primary"
                        @click="executeStep"
                        :disabled="!activeStep.actionForm.action"
                    >
                      执行步骤
                    </a-button>
                    <a-button @click="handleReset" :disabled="!rawModelResponse">重置修改</a-button>
                  </div>
                </a-form>
                <a-divider></a-divider>
                <a-card title="额外信息 (动态加载)">
                  <!-- [新功能] Schema 选择器 -->
                  <a-form-item label="标注模式">
                    <a-radio-group v-model:value="activeSchemaKey" button-style="solid">
                      <!-- 动态遍历 allExtraInfoSchemas 对象的键来生成按钮 -->
                      <a-radio-button
                          v-for="(schema, key) in allExtraInfoSchemas"
                          :key="key"
                          :value="key"
                      >
                        {{ key }}
                      </a-radio-button>
                    </a-radio-group>
                  </a-form-item>

                  <a-divider />
                  <!-- 确保 activeStep 和 schema 都已加载 -->
                  <a-form
                      v-if="activeStep && currentExtraInfoSchema.length > 0"
                      :model="activeStep.extra_info"
                      layout="vertical"
                  >
                    <!-- 遍历 Schema 来动态创建表单项 -->
                    <div v-for="field in currentExtraInfoSchema" :key="field.key">

                      <!-- ========================================================= -->
                      <!-- Case 1: 渲染简单字段 (例如：textarea, text, select)     -->
                      <!-- ========================================================= -->
                      <!-- 基本输入框 -->
                      <a-form-item v-if="field.type === 'text'" :label="field.label">
                        <a-input v-model:value="activeStep.extra_info[field.key]" :placeholder="field.placeholder" />
                      </a-form-item>

                      <a-form-item v-else-if="field.type === 'textarea'" :label="field.label">
                        <a-textarea v-model:value="activeStep.extra_info[field.key]" :placeholder="field.placeholder" :rows="4" />
                      </a-form-item>

                      <a-form-item v-else-if="field.type === 'number'" :label="field.label">
                        <a-input-number v-model:value="activeStep.extra_info[field.key]" :min="field.min" :max="field.max" style="width: 100%;" />
                      </a-form-item>

                      <!-- 选择器 -->
                      <a-form-item v-else-if="field.type === 'select'" :label="field.label">
                        <a-select v-model:value="activeStep.extra_info[field.key]" :options="field.options" />
                      </a-form-item>

                      <a-form-item v-else-if="field.type === 'checkbox'" :label="field.label">
                        <a-checkbox-group v-model:value="activeStep.extra_info[field.key]" :options="field.options" />
                      </a-form-item>

                      <a-form-item v-else-if="field.type === 'radio'" :label="field.label">
                        <a-radio-group v-model:value="activeStep.extra_info[field.key]" :options="field.options" option-type="button" button-style="solid" />
                      </a-form-item>

                      <!-- 其他控件 -->
                      <a-form-item v-else-if="field.type === 'switch'" :label="field.label">
                        <a-switch v-model:checked="activeStep.extra_info[field.key]" />
                      </a-form-item>

                      <a-form-item v-else-if="field.type === 'date'" :label="field.label">
                        <a-date-picker v-model:value="activeStep.extra_info[field.key]" :placeholder="field.placeholder" style="width: 100%;" />
                      </a-form-item>

                      <a-form-item v-else-if="field.type === 'slider'" :label="field.label">
                        <a-slider v-model:value="activeStep.extra_info[field.key]" :min="field.min" :max="field.max" :step="field.step" />
                      </a-form-item>

                      <!-- ========================================================= -->
                      <!-- Case 2: 渲染动态列表 (type: 'list') - [核心实现]         -->
                      <!-- ========================================================= -->
                      <div v-else-if="field.type === 'list'">
                        <!-- 使用 Divider 分隔，让 UI 更清晰 -->
                        <a-divider>{{ field.label }}</a-divider>

                        <!-- 遍历数据数组 (e.g., activeStep.extra_info.status) -->
                        <div
                            v-for="(item, index) in activeStep.extra_info[field.key]"
                            :key="index"
                            class="list-item-card"
                        >
                          <!-- 右上角的删除按钮 -->
                          <a-button
                              class="delete-btn"
                              danger
                              shape="circle"
                              size="small"
                              @click="removeListItem(field.key, index)"
                          >
                            <template #icon><delete-outlined /></template>
                          </a-button>

                          <!--
                            嵌套 v-for：遍历列表项的 schema (field.item_schema)
                            来为列表中的每个对象渲染内部表单。
                          -->
                          <a-form-item
                              v-for="subField in field.item_schema"
                              :key="subField.key"
                              :label="`${subField.label} #${index + 1}`"
                          >
                            <!-- 根据子字段的类型渲染对应的输入控件 -->
                            <a-input
                                v-if="subField.type === 'text'"
                                v-model:value="item[subField.key]"
                                :placeholder="subField.placeholder"
                            />
                            <a-textarea
                                v-else-if="subField.type === 'textarea'"
                                v-model:value="item[subField.key]"
                                :placeholder="subField.placeholder"
                                :rows="2"
                            />
                          </a-form-item>
                        </div>

                        <!-- 用于添加新列表项的按钮 -->
                        <a-button type="dashed" block @click="addListItem(field.key, field.item_schema)">
                          <plus-outlined /> 添加新条目
                        </a-button>
                      </div>
                    </div>

                  </a-form>
                  <a-empty v-else description="没有可配置的额外信息" />
                </a-card>
              </div>


            </a-skeleton>
          </a-card>
        </a-col>
      </a-row>
    </a-layout-content>

  </a-layout>
</template>

<style scoped>
.container {
  height: 100vh;
  width: 100vw;
  padding: 20px;
  margin: 0; /* 居中 */
}

.content {
  padding: 24px;
  background: #fff;
}

.screenshot-wrapper {
  flex: 1;
  overflow: hidden;
  border: 1px dashed #d9d9d9;
  position: relative;
  background-color: #fafafa;

  /* --- 新增样式：用于垂直和水平居中canvas元素 --- */
  display: flex;
  justify-content: center; /* 水平居中 */
  align-items: center;     /* 垂直居中 */
}

/* [修改] 样式现在应用到 canvas 上
设置图片显示高度为固定值
*/
.screenshot-img {
  display: block;
  height: 70vh;
}

.annotation-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>