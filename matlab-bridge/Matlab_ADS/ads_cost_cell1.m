function cost = ads_cost_cell1(d, wrk, x)
%ADS_COST_CELL1 cell_1 平行耦合线带通滤波器的代价函数（供 fminsearch）。
%   cost = ADS_COST_CELL1(d, wrk, x)
%
%   目标：2.5 GHz 带通
%     通带 2.0–3.0 GHz：S21 >= -1.5 dB，S11 <= -12 dB
%     阻带 <=1.5 或 >=3.5 GHz：S21 <= -20 dB
%
%   变量 x = [W1, S1, L1, L2, L3]（VAR1 中的尺寸，单位 mm），带物理边界裁剪。
%
%   依赖：先 ads_init()；d 为打开的 Design 对象；wrk 为工作区路径。

% ---- 1) 变量边界（裁剪，保证物理合理）----
lb = [0.3, 0.15, 5.0, 2.0, 3.0];
ub = [1.0, 1.00, 15.0, 8.0, 12.0];
xv = min(max(x, lb), ub);

% ---- 2) 更新 VAR1（W1,S1,L1,L2,L3）----
helper = py.importlib.import_module('ads_sim_helper');
names  = py.list({'W1','S1','L1','L2','L3'});
values = py.list({sprintf('%.4f', xv(1)), sprintf('%.4f', xv(2)), ...
                  sprintf('%.4f', xv(3)), sprintf('%.4f', xv(4)), sprintf('%.4f', xv(5))});
helper.set_var_eqn(d, 'VAR1', names, values);

% ---- 3) 仿真 + 读回 ----
out = ads_run_sim(d, wrk, 'cell_1');
s21dB = 20*log10(abs(out.data.S.S_2_1) + 1e-30);
s11dB = 20*log10(abs(out.data.S.S_1_1) + 1e-30);
f = out.data.freq_ghz;

% ---- 4) 代价：通带插损/回波 + 阻带抑制 ----
pass = (f >= 2.0) & (f <= 3.0);
stop = (f <= 1.5) | (f >= 3.5);
if any(pass)
    il = mean(max(0, -1.5 - s21dB(pass)));      % S21 通带插损（<=-1.5dB 不罚）
    rl = mean(max(0, s11dB(pass) + 12));        % S11 回波（<=-12dB 不罚）
else
    il = 20; rl = 20;
end
if any(stop)
    st = mean(max(0, s21dB(stop) + 20));        % 阻带抑制（<=-20dB 不罚）
else
    st = 0;
end
cost = 1.5*il + 1.5*rl + 1.0*st;

fprintf('[ads_cost_cell1] W1=%.3f S1=%.3f L1=%.2f L2=%.2f L3=%.2f  IL=%.2f RL=%.2f Stop=%.2f cost=%.4f\n', ...
    xv(1), xv(2), xv(3), xv(4), xv(5), il, rl, st, cost);
end
