// 这个文件不会被打包，可以在项目构建后直接修改。
// 注意：不要使用 ES6 模块语法 (import/export)，因为它是在 HTML 中通过 <script> 标签直接加载的。
window.APP_CONFIG ={
    // test
    testConfig: {
        test:''
    },
    // app列表
    appList : [
        {label:"京东", value:"jd"},
        {label:"淘宝", value:"taobao"},
        {label:"苏宁易购", value:"suning_com"},
        {label:"拼多多", value:"pinduoduo"},

        {label:"携程旅行", value:"ctrip"},
        {label:"滴滴出行", value:"didi_chuxing"},
        {label:"飞猪旅行", value:"fliggy"},

        {label:"高德地图", value:"amap"},
        {label:"百度地图", value:"baidu_maps"},
        {label:"腾讯地图", value:"tencent_maps"},

        {label:"美团", value:"meituan"},
        {label:"饿了吗", value:"eleme"},

        {label:"微信", value:"wechat"},
        {label:"QQ", value:"qq"},

        {label:"小红书", value:"xiaohongshu"},
        {label:"微博", value:"weibo"},

        {label:"钉钉", value:"dingtalk"},
        {label:"腾讯会议", value:"tencent_meeting"},

        {label:"飞书", value:"feishu_lark"},
        {label:"WPS Office", value:"wps_office"},

        {label:"便签", value:"notes"},
        {label:"相册", value:"gallery"},
        {label:"文件管理", value:"file_manager"},
        {label:"设置", value:"settings"},
        {label:"时钟", value:"clock"},
        {label:"日历", value:"calendar"},
        {label:"浏览器", value:"browser"},

        {label:"网易云音乐", value:"cloud_music"},
        {label:"酷我音乐", value:"kuwo_music"},
        {label:"酷狗音乐", value:"kugou_music"},
        {label:"QQ音乐", value:"qq_music"},

        {label:"有道云笔记", value:"youdao_note"},
        {label:"百度网盘", value:"baidu_netdisk"},
        {label:"Keep健身", value:"keep_fitness"},
        {label:"企业微信", value:"wecom"},

        {label:"抖音", value:"douyin"},
        {label:"腾讯视频", value:"txvideo"},
        {label:"爱奇艺", value:"aiqiyi"},
        {label:"B站", value:"bilibili"},

        {label:"今日头条", value:"toutiao"},
        {label:"新浪新闻", value:"sina_news"},
        {label:"网易新闻", value:"netease_news"},

        {label:"知乎", value:"zhihu"},

        {label:"YouTube", value:"youtube"},
        {label:"Google Drive", value:"google_drive"},
        {label:"Gmail", value:"gmail"},
        {label:"Outlook", value:"outlook"},
        {label:"Chrome", value:"chrome"},
        {label:"Zoom", value:"zoom"},

        {label:"支付宝", value:"alipay"},
        {label:"微信支付", value:"wechat_pay"}
    ],
    packageList : {
        "jd": "com.jingdong.app.mall",
        "taobao": "com.taobao.taobao",
        "suning_com": "com.suning.mobile.ebuy",
        "pinduoduo": "com.xunmeng.pinduoduo",

        "ctrip": "ctrip.android.view",
        "didi_chuxing": "com.sdu.didi.psnger",
        "fliggy": "com.taobao.trip",

        "amap": "com.autonavi.minimap",
        "baidu_maps": "com.baidu.BaiduMap",
        "tencent_maps": "com.tencent.map",

        "meituan": "com.sankuai.meituan",
        "eleme": "me.ele",

        "wechat": "com.tencent.mm",
        "qq": "com.tencent.mobileqq",

        "xiaohongshu": "com.xingin.xhs",
        "weibo": "com.sina.weibo",

        "dingtalk": "com.alibaba.android.rimet",
        "tencent_meeting": "com.tencent.wemeet",

        "feishu_lark": "com.ss.android.lark",
        "wps_office": "cn.wps.moffice_eng",

        "notes": "com.android.notes",
        "gallery": "com.android.gallery3d",
        "file_manager": "com.android.filemanager",
        "settings": "com.android.settings",
        "clock": "com.android.deskclock",
        "calendar": "com.google.android.calendar",
        "browser": "com.android.browser",

        "cloud_music": "com.netease.cloudmusic",
        "kuwo_music": "cn.kuwo.player",
        "kugou_music": "com.kugou.android",
        "qq_music": "com.tencent.qqmusic",

        "youdao_note": "com.youdao.note",
        "baidu_netdisk": "com.baidu.netdisk",
        "keep_fitness": "com.gotokeep.keep",
        "wecom": "com.tencent.wework",

        "douyin": "com.ss.android.ugc.aweme",
        "txvideo": "com.tencent.qqlive",
        "aiqiyi": "com.qiyi.video",
        "bilibili": "tv.danmaku.bili",

        "toutiao": "com.ss.android.article.news",
        "sina_news": "com.sina.news",
        "netease_news": "com.netease.newsreader.activity",

        "zhihu": "com.zhihu.android",

        "youtube": "com.google.android.youtube",
        "google_drive": "com.google.android.apps.docs",
        "gmail": "com.google.android.gm",
        "outlook": "com.microsoft.office.outlook",
        "chrome": "com.android.chrome",
        "zoom": "us.zoom.videomeetings",

        "alipay": "com.eg.android.AlipayGphone",
        "wechat_pay": "com.tencent.mm.plugin.wallet"
    },
    // step模版
    stepTemplate:{
        step_index: '1',// 这个值在创建时会被覆盖
        screenshot_64: "",
        screenshot_xml:"",
        actionForm: {
            "action": null,
            "x": null,
            "y": null,
            "value": '',
            "direction": 'up',
            "distance": 'medium',
            "x_end": null,
            "y_end": null,
            "app_value": ''
        },
        application: "",
        application_name_cn: "",
        application_name_en: "",
        extra_info: {
            // status内容
            //                {
            //                     content: "",
            //                     description: "",
            //                 }
            status: [

            ],
            reasoning: "",
            summary: "",
        }
    },
    allExtraInfoSchemas:{
        "friday":[
            {
                "key": "reasoning",
                "label": "推理过程",
                "type": "textarea",
                "placeholder": "请详细描述模型的推理过程或判定依据..."
            },
            {
                "key": "summary",
                "label": "步骤总结",
                "type": "textarea",
                "placeholder": "请输入对当前步骤的简短总结..."
            },
            {
                "key": "status",
                "label": "状态分析列表",
                "type": "list",
                "item_schema": [
                    {
                        "key": "content",
                        "label": "状态内容",
                        "type": "text",
                        "placeholder": "例如：按钮可点击"
                    },
                    {
                        "key": "description",
                        "label": "详细描述",
                        "type": "textarea",
                        "placeholder": "对该状态的详细说明"
                    }
                ]
            }
        ],
        // 举例：为另一个叫 "google_ui_automator" 的模式添加 schema
// in allExtraInfoSchemas object
        google_ui_automator: [
            // --- 基础类型 ---
            {
                "key": "element_id",
                "label": "目标元素ID (Text)",
                "type": "text",
                "placeholder": "请输入元素的 resource-id 或 xpath",
                "defaultValue": ""
            },
            {
                "key": "description",
                "label": "步骤描述 (Textarea)",
                "type": "textarea",
                "placeholder": "详细描述此自动化步骤的目的...",
                "defaultValue": ""
            },
            {
                "key": "timeout_seconds",
                "label": "超时时间(秒) (Number)",
                "type": "number",
                "min": 0,
                "max": 300,
                "defaultValue": 30
            },
            // --- 选择类型 ---
            {
                "key": "assertion_type",
                "label": "断言类型 (Select)",
                "type": "select",
                "options": [
                    { "label": "元素存在", "value": "EXISTS" },
                    { "label": "元素不存在", "value": "NOT_EXISTS" },
                    { "label": "元素可点击", "value": "IS_CLICKABLE" },
                    { "label": "包含文本", "value": "HAS_TEXT" }
                ],
                "defaultValue": "EXISTS"
            },
            {
                "key": "check_flags",
                "label": "检查标志 (Checkbox)",
                "type": "checkbox",
                "options": [
                    { "label": "可见", "value": "VISIBLE" },
                    { "label": "已启用", "value": "ENABLED" },
                    { "label": "已聚焦", "value": "FOCUSED" }
                ],
                "defaultValue": ["VISIBLE"]
            },
            {
                "key": "execution_priority",
                "label": "执行优先级 (Radio)",
                "type": "radio",
                "options": [
                    { "label": "低", "value": "LOW" },
                    { "label": "中", "value": "MEDIUM" },
                    { "label": "高", "value": "HIGH" }
                ],
                "defaultValue": "MEDIUM"
            },
            // --- 其他控件类型 ---
            {
                "key": "is_critical_step",
                "label": "是否为关键步骤 (Switch)",
                "type": "switch",
                "defaultValue": true
            },
            {
                "key": "execution_date",
                "label": "计划执行日期 (Date)",
                "type": "date",
                "placeholder": "选择一个日期",
                "defaultValue": null
            },
            {
                "key": "confidence_level",
                "label": "置信度阈值 (Slider)",
                "type": "slider",
                "min": 0,
                "max": 1,
                "step": 0.01,
                "defaultValue": 0.95
            },
            // --- 复杂类型 ---
            {
                "key": "validation_steps",
                "label": "后续验证步骤 (List)",
                "type": "list",
                "item_schema": [
                    {
                        "key": "selector",
                        "label": "验证选择器",
                        "type": "text",
                        "placeholder": "输入用于验证的元素选择器"
                    },
                    {
                        "key": "validation_type",
                        "label": "验证类型",
                        "type": "select",
                        "options": [
                            { "label": "应可见", "value": "SHOULD_BE_VISIBLE" },
                            { "label": "应隐藏", "value": "SHOULD_BE_HIDDEN" }
                        ]
                    }
                ]
            }
        ]
    },
    activeSchemaKey:'friday',
    actionTypes : [
        { label: '点击 (tap)', value: 'tap' },
        { label: '输入文本 (text)-暂时无法执行', value: 'text' },
        { label: '需要反馈 (need_feedback)', value: 'need_feedback' },
        { label: '长按 (long_press)', value: 'long_press' },
        { label: '滑动 (swipe)', value: 'swipe' },
        { label: '滑动 (swipe_two_points)', value: 'swipe_two_points' },
        { label: '等待 (wait)', value: 'wait' },
        { label: '结束 (FINISH)', value: 'FINISH' },
        { label: '打开应用(open_app)-暂时无法执行',value: 'open_app' },

        { label: '截图(capture_screen)-暂时无法执行',value:'capture_screen'},
        { label: '返回主页(home)-暂时无法执行',value:'home'},
        { label: '返回上一页(back)-暂时无法执行',value:'back'}
    ]
}