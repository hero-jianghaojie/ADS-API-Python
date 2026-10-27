function cost = ads_lpf_cost(d, wrk, x, fc_target)
%ADS_LPF_COST 低通滤波器优化代价函数（供 fminsearch 调用）。
%   cost = ADS_LPF_COST(d, wrk, x, fc_target)
%
%   设置 TL2.L/TL4.L/TL6.L（TL6 镜像 TL2），跑仿真，计算代价：
%     - 代价 = (实测 -3dB 截止频率 - 目标频率)^2
%     - 附加通带惩罚：S21@1GHz 不得劣于 -1.5 dB
%
%   x = [L2_mm, L4_mm]  （TL6.L 与 TL2.L 同步，保持对称）
%
%   依赖：先 ads_init()；d 为打开的 Design 对象。

% 1) 应用参数（mm -> 'x mm'）
l2 = sprintf('%.4f mm', x(1));
l4 = sprintf('%.4f mm', x(2));
ads_set_param(d, {'TL2', 'L', l2; 'TL4', 'L', l4; 'TL6', 'L', l2});

% 2) 跑仿真并读回
out = ads_run_sim(d, wrk, 'py_ms_lpf');
s21dB = 20*log10(abs(out.data.S.S_2_1) + 1e-30);
fGHz  = out.data.freq_ghz;

% 3) 找 -3dB 截止频率（s21dB 随频率单调下降 → 反转后插值）
s21r = s21dB(end:-1:1);
fr   = fGHz(end:-1:1);
fc = interp1(s21r, fr, -3, 'linear', fc_target + 10);
if isnan(fc)
    fc = fc_target + 10;   % 没交叉 = 严重偏离
end

% 4) 通带惩罚：S21@1GHz 必须 > -1.5 dB
ipass = find(fGHz <= 1, 1, 'last');
pass = s21dB(ipass);
penalty = 5 * max(0, -1.5 - pass);

cost = (fc - fc_target)^2 + penalty;
fprintf('[ads_lpf_cost] L2=%.4f L4=%.4f  fc=%.3fGHz  pass=%.2fdB  cost=%.4f\n', ...
    x(1), x(2), fc, pass, cost);
end
