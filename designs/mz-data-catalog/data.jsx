/* data.jsx — 目录数据与工具函数
   ⚠️ 每个 <script type="text/babel"> 有独立作用域 → 必须挂到 window 才能被其他文件用 */

const CATALOG = [
  { id:1,  name:'低保对象基础信息',        code:'MZ-SH-0001', org:'省民政厅社会救助处',
    share:'无条件共享', size:126000, cycle:'每月', updated:'2026-10-06', status:'已发布', level:'低', masked:false,
    desc:'全省城乡最低生活保障对象的基本信息、家庭成员构成、救助金额与发放记录。',
    fields:[['xm','string','姓名'],['sfzh','string','身份证号（脱敏）'],['bjje','decimal','本月保障金额'],['cjsj','datetime','数据产生时间']] },

  { id:2,  name:'特困人员供养信息',        code:'MZ-SH-0002', org:'省民政厅社会救助处',
    share:'无条件共享', size:34000, cycle:'每月', updated:'2026-10-06', status:'已发布', level:'低', masked:false,
    desc:'特困人员救助供养对象、供养方式、供养标准及资金发放情况。',
    fields:[['xm','string','姓名'],['gyfs','string','供养方式'],['gybz','decimal','供养标准'],['rdrq','date','认定日期']] },

  { id:3,  name:'养老服务设施台账',        code:'MZ-YL-0007', org:'省民政厅养老服务处',
    share:'有条件共享', size:8120, cycle:'每季度', updated:'2026-10-05', status:'已发布', level:'中', masked:false,
    desc:'全省养老机构、社区养老服务设施的基础信息、床位规模与运营主体。',
    fields:[['jdmc','string','机构名称'],['dj','string','机构等级'],['cws','int','床位数'],['dz','string','详细地址']] },

  { id:4,  name:'社会组织登记信息',        code:'MZ-ZZ-0021', org:'省民政厅社会组织管理局',
    share:'有条件共享', size:57000, cycle:'每月', updated:'2026-10-05', status:'待审核', level:'中', masked:false,
    desc:'社会组织成立、变更、注销登记信息及年度检查结论。',
    fields:[['zzmc','string','组织名称'],['tyshxydm','string','统一社会信用代码'],['djrq','date','登记日期'],['zt','string','登记状态']] },

  { id:5,  name:'婚姻登记信息（脱敏）',    code:'MZ-SW-0003', org:'省民政厅社会事务处',
    share:'有条件共享', size:2860000, cycle:'每日', updated:'2026-10-04', status:'已发布', level:'高', masked:true,
    desc:'婚姻登记记录。身份证号、住址等敏感字段已按分类分级要求脱敏。',
    fields:[['jhdjsj','date','结婚登记时间'],['sfzh','string','身份证号（脱敏）'],['djjg','string','登记机关']] },

  { id:6,  name:'殡葬服务单位信息',        code:'MZ-SW-0011', org:'省民政厅社会事务处',
    share:'无条件共享', size:1036, cycle:'每季度', updated:'2026-10-03', status:'已发布', level:'低', masked:false,
    desc:'殡仪馆、公墓等殡葬服务单位的基本情况与服务能力。',
    fields:[['dwmc','string','单位名称'],['lxdh','string','联系电话'],['dz','string','地址']] },

  { id:7,  name:'残疾人两项补贴发放信息',  code:'MZ-CJ-0005', org:'省民政厅残疾人福利处',
    share:'无条件共享', size:248000, cycle:'每月', updated:'2026-10-03', status:'已发布', level:'中', masked:true,
    desc:'困难残疾人生活补贴、重度残疾人护理补贴的发放对象与金额明细。',
    fields:[['xm','string','姓名'],['btlx','string','补贴类型'],['ffje','decimal','发放金额'],['ffyf','string','发放月份']] },

  { id:8,  name:'行政区划与地名数据',      code:'MZ-QH-0001', org:'省民政厅区划地名处',
    share:'无条件共享', size:42000, cycle:'每半年', updated:'2026-10-02', status:'已发布', level:'低', masked:false,
    desc:'行政区划代码、层级、变更沿革以及标准地名信息。',
    fields:[['qhdm','string','行政区划代码'],['qhmc','string','名称'],['jb','string','层级']] },

  { id:9,  name:'儿童福利机构信息',        code:'MZ-ET-0002', org:'省民政厅儿童福利处',
    share:'有条件共享', size:418, cycle:'每季度', updated:'2026-10-01', status:'已发布', level:'中', masked:false,
    desc:'儿童福利院、未成年人保护机构的基础信息与床位使用情况。',
    fields:[['jdmc','string','机构名称'],['cws','int','床位数'],['lxr','string','联系人']] },

  { id:10, name:'慈善组织公开募捐信息',    code:'MZ-CS-0003', org:'省民政厅慈善事业促进处',
    share:'无条件共享', size:21000, cycle:'每月', updated:'2026-09-30', status:'已发布', level:'低', masked:false,
    desc:'慈善组织公开募捐方案备案信息与募捐进展。',
    fields:[['zzmc','string','组织名称'],['fa','string','募捐方案'],['je','decimal','募得金额']] },

  { id:11, name:'高龄津贴发放信息',        code:'MZ-YL-0019', org:'省民政厅养老服务处',
    share:'无条件共享', size:382000, cycle:'每月', updated:'2026-09-29', status:'已发布', level:'中', masked:true,
    desc:'高龄老人津贴发放对象、标准与逐月发放记录。',
    fields:[['xm','string','姓名'],['nl','int','年龄'],['btbz','decimal','补贴标准'],['ffyf','string','发放月份']] },

  { id:12, name:'社会组织年检结果',        code:'MZ-ZZ-0044', org:'省民政厅社会组织管理局',
    share:'不予共享', size:18000, cycle:'每年', updated:'2026-09-28', status:'已下架', level:'高', masked:true,
    desc:'社会组织年度检查结论与整改情况，仅限内部监管使用。',
    fields:[['zzmc','string','组织名称'],['njjl','string','年检结论'],['zgqk','string','整改情况']] },

  { id:13, name:'社会救助家庭经济状况核对', code:'MZ-SH-0009', org:'省民政厅社会救助处',
    share:'有条件共享', size:96000, cycle:'每月', updated:'2026-09-26', status:'已发布', level:'高', masked:true,
    desc:'低保、特困等救助对象的家庭经济状况核对结果与疑似问题清单。',
    fields:[['xm','string','姓名'],['hdbm','string','核对部门'],['hdyy','string','核对原因'],['hdrq','date','核对日期']] },

  { id:14, name:'志愿服务组织与项目',      code:'MZ-CS-0017', org:'省民政厅慈善事业促进处',
    share:'无条件共享', size:15400, cycle:'每季度', updated:'2026-09-25', status:'已发布', level:'低', masked:false,
    desc:'志愿服务组织备案信息与志愿服务项目实施情况。',
    fields:[['zzmc','string','组织名称'],['xmmc','string','项目名称'],['fwsc','int','服务时长']] },
];

const MY_APPLIES = [
  { no:'SQ1001', catalog:'养老服务设施台账', org:'省民政厅信息中心', term:'1 年', time:'2026-09-28 10:12', status:'已通过' },
  { no:'SQ1002', catalog:'行政区划与地名数据', org:'省民政厅信息中心', term:'长期', time:'2026-09-30 15:40', status:'待审核' },
];

const CYCLE_OPTIONS = ['1 年', '6 个月', '3 个月', '长期'];

const SHARE_FILTERS = ['全部', '无条件共享', '有条件共享', '不予共享'];

/* 工具函数 */
function fmtNum(n){
  return n.toLocaleString('zh-CN');
}
function sizeText(n){
  if (n >= 10000) return (n / 10000).toFixed(1) + ' 万条';
  return fmtNum(n) + ' 条';
}
function shareClass(s){
  if (s === '无条件共享') return 'share share-free';
  if (s === '有条件共享') return 'share share-cond';
  return 'share share-none';
}
function statusClass(s){
  if (s === '已发布') return 'st st-pub';
  if (s === '待审核') return 'st st-rev';
  return 'st st-off';
}
function nowStamp(){
  const d = new Date();
  const p = x => (x < 10 ? '0' : '') + x;
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

Object.assign(window, {
  CATALOG, MY_APPLIES, CYCLE_OPTIONS, SHARE_FILTERS,
  fmtNum, sizeText, shareClass, statusClass, nowStamp,
});
