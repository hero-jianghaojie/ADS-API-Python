%% demo_plot_s21.m
% Demo: MATLAB 读取 ADS 仿真数据集并绘图（验证联合仿真数据流闭环）
% Run: matlab -batch "demo_plot_s21"
clear; clc;
out = read_ads_dataset('D:\AppGallery\codex\ADS\python_wrk\data\py_ms_lpf.ds');

s21dB = 20*log10(abs(out.S.S_2_1)+1e-30);
s11dB = 20*log10(abs(out.S.S_1_1)+1e-30);

f = figure('Visible','off','Color','w');
plot(out.freq_ghz, s21dB, 'b-', 'LineWidth', 1.6); hold on;
plot(out.freq_ghz, s11dB, 'g-', 'LineWidth', 1.6);
grid on; legend('S21','S11','Location','south');
xlabel('Frequency (GHz)'); ylabel('Magnitude (dB)');
title(sprintf('ADS %s  (read via MATLAB-Python-ADS bridge, %d pts)', ...
    out.varblock, out.points));
saveas(f, 'py_ms_lpf_s21.png');
fprintf('saved: py_ms_lpf_s21.png\n');
close(f);
