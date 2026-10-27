%% demo_optimize.m
% MATLAB 自动调参闭环：用 fminsearch 优化 ADS 低通滤波器截止频率。
%   目标：把 -3dB 截止频率优化到 2.0 GHz
%   变量：TL2.L、TL4.L（TL6.L 与 TL2.L 镜像同步）
%   循环：MATLAB 设参 -> ADS(hpeesofsim) 仿真 -> 读回 S 参数 -> 算代价 -> 更新参数
%
% 运行（未激活 venv 的终端）：
%   matlab -batch "demo_optimize"
%
% 依赖：ads_init / ads_set_param / ads_run_sim / ads_lpf_cost / ads_sim_helper.py
clear; clc;

FC_TARGET = 2.0;            % 目标 -3dB 截止频率 (GHz)
WRK  = 'D:\AppGallery\codex\ADS\python_wrk';
CELL = 'python_lib:py_ms_lpf:schematic';

% ---- 初始化桥 + 打开设计（APPEND 模式，允许保存） ----
[de, ds] = ads_init();
ws = de.open_workspace(WRK);
d  = ws.design(CELL, de.db.DesignMode.APPEND);

% ---- 记录初始参数 ----
l2_0 = char(d.find_instance('TL2').parameters('L').value);
l4_0 = char(d.find_instance('TL4').parameters('L').value);
fprintf('初始参数: TL2.L=%s, TL4.L=%s\n', l2_0, l4_0);
x0 = [str2double(strtok(l2_0,' ')), str2double(strtok(l4_0,' '))];

% ---- 先跑一次基准，看当前截止频率 ----
out0 = ads_run_sim(d, WRK, 'py_ms_lpf');
s210 = 20*log10(abs(out0.data.S.S_2_1) + 1e-30);
fc0 = interp1(s210(end:-1:1), out0.data.freq_ghz(end:-1:1), -3, 'linear');
fprintf('当前 -3dB 截止频率 ≈ %.3f GHz（目标 %.1f GHz）\n', fc0, FC_TARGET);

% ---- fminsearch 优化 ----
costfun = @(x) ads_lpf_cost(d, WRK, x, FC_TARGET);
opts = optimset('Display', 'iter', 'TolX', 0.02, 'TolFun', 0.5, 'MaxFunEvals', 24);
[xopt, fmin] = fminsearch(costfun, x0, opts);

% ---- 应用最优并最终验证 ----
ads_set_param(d, {'TL2','L',sprintf('%.4f mm',xopt(1));
                  'TL4','L',sprintf('%.4f mm',xopt(2));
                  'TL6','L',sprintf('%.4f mm',xopt(1))});
d.save_design();   % 保存最优值到原理图（APPEND 模式必需）
fprintf('[demo_optimize] 已保存最优参数到原理图\n');
outf = ads_run_sim(d, WRK, 'py_ms_lpf');
s21f = 20*log10(abs(outf.data.S.S_2_1) + 1e-30);
fcf = interp1(s21f(end:-1:1), outf.data.freq_ghz(end:-1:1), -3, 'linear');

fprintf('\n===== 优化完成 =====\n');
fprintf('初始: L2=%s L4=%s  ->  最优: L2=%.4fmm L4=%.4fmm\n', l2_0, l4_0, xopt(1), xopt(2));
fprintf('截止频率: %.3f GHz -> %.3f GHz (目标 %.1f GHz)\n', fc0, fcf, FC_TARGET);
fprintf('最小代价: %.4f\n', fmin);

% ---- 出对比图 ----
f = figure('Visible','off','Color','w');
plot(out0.data.freq_ghz, s210, 'b-', 'LineWidth', 1.5); hold on;
plot(outf.data.freq_ghz, s21f, 'r--', 'LineWidth', 1.5);
yline(-3, 'k:'); grid on;
legend('初始 S21','优化后 S21','-3dB','Location','southwest');
xlabel('Frequency (GHz)'); ylabel('S21 (dB)');
title(sprintf('LPF 优化: fc %.3f -> %.3f GHz (目标 %.1f)', fc0, fcf, FC_TARGET));
saveas(f, 'optimize_result.png');
fprintf('已保存: optimize_result.png\n');
close(f);
