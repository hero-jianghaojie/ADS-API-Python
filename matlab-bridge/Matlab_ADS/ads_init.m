function [de, ds] = ads_init(ads_dir)
%ADS_INIT 初始化 MATLAB -> ADS Python (keysight.ads) 桥接。
%   [de, ds] = ADS_INIT() 使用默认 ADS 安装目录初始化，返回：
%     de - keysight.ads.de 模块（设计自动化）
%     ds - keysight.ads.dataset 模块（读仿真数据集）
%
%   必须在调用任何 keysight.ads 函数之前先调用本函数。
%   注意：请勿在激活了其他 Python venv 的终端里运行（MATLAB 可能选中错误的解释器）。
%
%   Example:
%     [de, ds] = ads_init();
%     ws = de.open_workspace('D:\AppGallery\codex\ADS\python_wrk');

if nargin < 1 || isempty(ads_dir)
    ads_dir = 'D:\Program Files\Keysight\ADS2025_Update2';
end
ADS_PY = fullfile(ads_dir, 'tools', 'python', 'python.exe');

% 1) 强制使用 ADS 自带 Python，并用 OutOfProcess 模式避免 DLL 冲突
pyenv('Version', ADS_PY, 'ExecutionMode', 'OutOfProcess');
pe = pyenv;
assert(strcmp(char(pe.Version), '3.12'), ...
    'pyenv 版本应为 3.12（ADS 自带 Python），实际为 %s。', char(pe.Version));

% 2) HPEESOF_DIR 必须在 import keysight.ads 之前设置
setenv('HPEESOF_DIR', ads_dir);
assert(logical(exist(ads_dir, 'dir')), 'ADS 目录不存在: %s', ads_dir);

% 3) 导入模块（首次调用会启动 ADS 自动化进程，稍慢）
de = py.importlib.import_module('keysight.ads.de');
ds = py.importlib.import_module('keysight.ads.dataset');

% 4) 把 Matlab_ADS 目录加入 Python 路径（供 ads_sim_helper 等使用）
persistent path_ready
if isempty(path_ready)
    sp = py.sys.path;
    sp.insert(int64(0), fileparts(mfilename('fullpath')));
    path_ready = true;
end

fprintf('[ads_init] MATLAB -> ADS Python bridge OK (ADS %s)\n', ...
    char(de.version()));
end

