function out = ads_run_sim(d, wrk, design_name)
%ADS_RUN_SIM 生成网表并运行 hpeesofsim 仿真，读回新数据集。
%   out = ADS_RUN_SIM(d, wrk, design_name)
%
%   输入：
%     d            - de 打开的 Design 对象
%     wrk          - ADS 工作区目录（字符串）
%     design_name  - 设计名（如 'py_ms_lpf'），决定网表名与 .ds 名
%
%   输出：
%     out.ds_path  - 新生成的 .ds 数据集路径
%     out.data     - read_ads_dataset 的结果结构体（含 freq_ghz / S 等）
%
%   示例：
%     [de,ds] = ads_init();
%     ws = de.open_workspace('...\python_wrk');
%     d  = ws.design('python_lib:py_ms_lpf:schematic');
%     out = ads_run_sim(d, '...\python_wrk', 'py_ms_lpf');
%     plot(out.data.freq_ghz, 20*log10(abs(out.data.S.S_2_1)));
%
%   说明：仿真由 Python 助手 ads_sim_helper.py 完成（负责搭建 hpeesofsim
%   完整环境）。每次运行会覆盖 <wrk>/<design_name>.ds，返回最新结果。

% 确保 Python 助手可导入
persistent path_ready
if isempty(path_ready)
    sp = py.sys.path;
    sp.insert(int64(0), 'd:\AppGallery\codex\Matlab_ADS');
    path_ready = true;
end

% 1) 生成网表
nl = char(d.generate_netlist());
if isempty(strtrim(nl))
    error('ADS_RUN_SIM: netlist 为空');
end

% 2) 调用 Python 助手跑 hpeesofsim（显式 import，避免 py. 点路径解析问题）
helper = py.importlib.import_module('ads_sim_helper');
r = helper.run_hpeesofsim(nl, wrk, design_name);
ok = logical(r.get('ok'));
if ~ok
    rc = int64(r.get('rc'));
    tail = char(r.get('stdout_tail'));
    err = char(r.get('stderr'));
    error('ADS_RUN_SIM: 仿真失败 rc=%d\n--- stdout ---\n%s\n--- stderr ---\n%s', rc, tail, err);
end

out.ds_path = char(r.get('ds_path'));

% 3) 读回新数据集
out.data = read_ads_dataset(out.ds_path);
fprintf('[ads_run_sim] OK: %d points, %.3f-%.3f GHz, S21@1GHz=%.2f dB\n', ...
    out.data.points, out.data.freq_ghz(1), out.data.freq_ghz(end), ...
    20*log10(abs(out.data.S.S_2_1(find(out.data.freq_ghz >= 1, 1))) + 1e-30));
end
