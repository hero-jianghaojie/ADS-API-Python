%% test_e2e_ads.m
% End-to-end feasibility: MATLAB -> keysight.ads (Python) -> ADS
%  1) open ADS workspace
%  2) list libraries / open design & generate netlist (drive ADS design automation)
%  3) read back a .ds dataset & process S-parameters in pure MATLAB
% Run (clean env, no venv activated):  matlab -batch "test_e2e_ads"
clear; clc;
ADS_PY  = 'D:\Program Files\Keysight\ADS2025_Update2\tools\python\python.exe';
ADS_DIR = 'D:\Program Files\Keysight\ADS2025_Update2';
WRK     = 'D:\AppGallery\codex\ADS\python_wrk';
DS_PATH = 'D:\AppGallery\codex\ADS\python_wrk\data\py_ms_lpf.ds';

pyenv('Version', ADS_PY, 'ExecutionMode', 'OutOfProcess');
setenv('HPEESOF_DIR', ADS_DIR);

fprintf('===== [1] import keysight.ads =====\n');
de = py.importlib.import_module('keysight.ads.de');
ds = py.importlib.import_module('keysight.ads.dataset');
fprintf('OK: keysight.ads.de + keysight.ads.dataset imported\n');

fprintf('\n===== [2] open ADS workspace =====\n');
ws = de.open_workspace(WRK);
fprintf('workspace path: %s\n', char(ws.path));

fprintf('\n===== [3] list libraries =====\n');
try
    ln = cell(py.list(ws.library_names));
    fprintf('library_names: %s\n', strjoin(cellfun(@char, ln, 'UniformOutput', false), ', '));
catch ME
    fprintf('(list libraries) %s\n', ME.message);
end

fprintf('\n===== [4] open design & generate netlist (drive ADS) =====\n');
try
    d = ws.design('python_lib:py_ms_lpf:schematic');
    fprintf('design: %s\n', char(d.design_name));
    nl = d.generate_netlist();
    fprintf('netlist generated: %d chars\n', int64(py.len(nl)));
    lines = cell(nl.splitlines());
    fprintf('  first line: %s\n', char(lines{1}));
catch ME
    fprintf('generate_netlist: %s\n', ME.message);
end

fprintf('\n===== [5] read ADS dataset (.ds) from MATLAB =====\n');
dset = ds.open_dataset_for_reading(DS_PATH);
fprintf('dataset path: %s\n', char(dset.path));
vb = dset.get('SP1.SP');
df = vb.to_dataframe();
freq = double(df.index.to_numpy());            % Hz
s21  = double(df.get('S[2,1]').to_numpy());    % complex
s11  = double(df.get('S[1,1]').to_numpy());    % complex
fprintf('points: %d, freq range: %.3f - %.3f GHz\n', ...
    numel(freq), freq(1)/1e9, freq(end)/1e9);

fprintf('\n===== [6] process S-params in pure MATLAB =====\n');
fGHz = freq / 1e9;
s21dB = 20*log10(abs(s21)+1e-30);
s11dB = 20*log10(abs(s11)+1e-30);
sel = find(mod(round(fGHz*10),10)==0);
for i = sel(1:min(5,numel(sel)))
    fprintf('  f=%.3f GHz   S21=%.2f dB   S11=%.2f dB\n', fGHz(i), s21dB(i), s11dB(i));
end

fprintf('\n===== E2E RESULT: SUCCESS =====\n');
