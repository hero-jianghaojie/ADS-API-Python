%% demo_optimize_cell1.m
% 优化 cell_1（平行耦合线带通滤波器）的带内性能。
%   目标：2.5 GHz 带通（通带 2-3GHz：S21>=-1.5dB, S11<=-12dB；阻带<=-20dB）
%   变量：VAR1 的 W1,S1,L1,L2,L3（fminsearch）
%   循环：MATLAB 设 VAR1 -> ADS(hpeesofsim) 仿真 -> 读回 S 参数 -> 代价 -> 更新
%
% 运行（未激活 venv 的终端）：matlab -batch "demo_optimize_cell1"
clear; clc;

WRK  = 'D:\AppGallery\codex\ADS\python_wrk';
CELL = 'python_lib:cell_1:schematic';

% ---- 初始化 + 打开设计（APPEND 模式，允许保存到原理图） ----
[de, ds] = ads_init();
ws = de.open_workspace(WRK);
d  = ws.design(CELL, de.db.DesignMode.APPEND);

% ---- 读取 VAR1 初始值 ----
helper = py.importlib.import_module('ads_sim_helper');
var1 = d.find_instance('VAR1').parameters('Variable Value').value;
n0 = cellfun(@(c) char(c{1}), cell(var1), 'UniformOutput', false);
v0 = cellfun(@(c) char(c{2}), cell(var1), 'UniformOutput', false);
getv = @(n) str2double(v0{strcmp(n0,n)});
x0 = [getv('W1'), getv('S1'), getv('L1'), getv('L2'), getv('L3')];
fprintf('初始 VAR1: W1=%.4f S1=%.4f L1=%.4f L2=%.4f L3=%.4f\n', x0);

% ---- 基准仿真 ----
out0 = ads_run_sim(d, WRK, 'cell_1');
s210 = 20*log10(abs(out0.data.S.S_2_1) + 1e-30);
s110 = 20*log10(abs(out0.data.S.S_1_1) + 1e-30);
f0 = out0.data.freq_ghz;
p0 = (f0>=2.0)&(f0<=3.0);
fprintf('基准: 通带均值 S21=%.2f dB, S11=%.2f dB\n', mean(s210(p0)), mean(s110(p0)));

% ---- fminsearch 优化 ----
costfun = @(x) ads_cost_cell1(d, WRK, x);
opts = optimset('Display','iter','TolX',0.02,'TolFun',0.3,'MaxFunEvals',50);
[xopt, fmin] = fminsearch(costfun, x0, opts);

% ---- 应用最优并最终验证 ----
helper.set_var_eqn(d, 'VAR1', py.list({'W1','S1','L1','L2','L3'}), ...
    py.list({sprintf('%.4f',xopt(1)),sprintf('%.4f',xopt(2)),sprintf('%.4f',xopt(3)),...
             sprintf('%.4f',xopt(4)),sprintf('%.4f',xopt(5))}));
d.save_design();   % 保存最优值到原理图（APPEND 模式必需）
fprintf('[demo_optimize_cell1] 已保存最优参数到原理图\n');
outf = ads_run_sim(d, WRK, 'cell_1');
s21f = 20*log10(abs(outf.data.S.S_2_1) + 1e-30);
s11f = 20*log10(abs(outf.data.S.S_1_1) + 1e-30);
ff = outf.data.freq_ghz;
pf = (ff>=2.0)&(ff<=3.0);

fprintf('\n===== 优化完成 =====\n');
fprintf('初始: W1=%.3f S1=%.3f L1=%.2f L2=%.2f L3=%.2f\n', x0);
fprintf('最优: W1=%.3f S1=%.3f L1=%.2f L2=%.2f L3=%.2f\n', xopt);
fprintf('通带均值: S21 %.2f -> %.2f dB,  S11 %.2f -> %.2f dB\n', ...
    mean(s210(p0)), mean(s21f(pf)), mean(s110(p0)), mean(s11f(pf)));
fprintf('最小代价: %.4f\n', fmin);

% ---- 出对比图 ----
f = figure('Visible','off','Color','w');
subplot(2,1,1);
plot(f0, s210, 'b-', 'LineWidth',1.4); hold on;
plot(ff, s21f, 'r--', 'LineWidth',1.4);
yline(-1.5,'k:'); yline(-20,'k:'); grid on;
legend('初始 S21','优化后 S21','-1.5dB','-20dB','Location','southwest');
xlabel('Frequency (GHz)'); ylabel('S21 (dB)');
title('cell_1 带通滤波器优化（S21）'); ylim([-60 5]);
subplot(2,1,2);
plot(f0, s110, 'b-', 'LineWidth',1.4); hold on;
plot(ff, s11f, 'r--', 'LineWidth',1.4);
yline(-12,'k:'); grid on;
legend('初始 S11','优化后 S11','-12dB','Location','south');
xlabel('Frequency (GHz)'); ylabel('S11 (dB)');
title('cell_1 带通滤波器优化（S11）'); ylim([-40 5]);
saveas(f, 'optimize_cell1_result.png');
fprintf('已保存: optimize_cell1_result.png\n');
close(f);
