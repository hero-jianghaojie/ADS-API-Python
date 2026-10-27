%% test_matlab_python_ads.m
% 可行性验证：MATLAB R2025a 调用 ADS 自带 Python (3.12.2) + keysight.ads.de
% 运行： matlab -batch "test_matlab_python_ads"
clear; clc;

fprintf('=== MATLAB Version ===\n');
disp(version);

ADS_PY = 'D:\Program Files\Keysight\ADS2025_Update2\tools\python\python.exe';
ADS_DIR = 'D:\Program Files\Keysight\ADS2025_Update2';

fprintf('\n=== 强制 pyenv 指向 ADS 自带 Python（OutOfProcess 避免 DLL 冲突） ===\n');
pyenv('Version', ADS_PY, 'ExecutionMode', 'OutOfProcess');
pe = pyenv;
disp(pe);
fprintf('Python Version: %s\n', pe.Version);

fprintf('\n=== 设置 HPEESOF_DIR（keysight.ads 需要） ===\n');
setenv('HPEESOF_DIR', ADS_DIR);
fprintf('HPEESOF_DIR=%s\n', getenv('HPEESOF_DIR'));

fprintf('\n=== 导入 keysight.ads.de ===\n');
try
    de = py.importlib.import_module('keysight.ads.de');
    fprintf('OK: keysight.ads.de 导入成功\n');
    % 检查可调用函数
    fn = {'open_workspace','create_workspace','active_workspace','version'};
    for i = 1:numel(fn)
        if py.hasattr(de, fn{i})
            fprintf('  - %s 可用\n', fn{i});
        end
    end
catch ME
    fprintf('FAIL: %s\n', ME.message);
    rethrow(ME);
end

fprintf('\n=== 检查是否有 ADS 进程在运行 / workspace ===\n');
try
    aw = de.active_workspace();
    fprintf('active workspace: %s\n', char(aw));
catch ME
    fprintf('（无激活 workspace，正常）%s\n', ME.message);
end

fprintf('\n=== 可行性结论 ===\n');
fprintf('MATLAB -> Python(keysight.ads.de) -> ADS 桥接：成功\n');
