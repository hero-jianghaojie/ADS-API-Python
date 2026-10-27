function out = read_ads_dataset(ds_path, varargin)
%READ_ADS_DATASET 用 MATLAB 读取 ADS .ds 仿真数据集（S 参数）。
%   out = READ_ADS_DATASET(ds_path) 读取 S 参数仿真数据集，返回结构体：
%     out.freq      - 频率 (Hz)，列向量
%     out.freq_ghz  - 频率 (GHz)，列向量
%     out.S         - 结构体，字段 'S[1,1]','S[2,1]',... 复数矩阵（列向量）
%     out.varblock  - 读取到的变量块名（默认第一个）
%     out.points    - 频点数
%
%   READ_ADS_DATASET(ds_path, 'VarBlock', 'SP1.SP') 指定变量块。
%
%   Example:
%     out = read_ads_dataset('D:\AppGallery\codex\ADS\python_wrk\data\py_ms_lpf.ds');
%     plot(out.freq_ghz, 20*log10(abs(out.S.S21)));
%
%   依赖：先运行 ads_init 建立 MATLAB->ADS Python 桥接。

p = inputParser;
addParameter(p, 'VarBlock', '', @ischar);
parse(p, varargin{:});
vbname = p.Results.VarBlock;

% 复用/初始化桥
persistent ds;
if isempty(ds)
    [~, ds] = ads_init();
end

dset = ds.open_dataset_for_reading(ds_path);
vbs  = cell(py.list(dset.varblock_names));
if isempty(vbname)
    % 默认取第一个变量块
    vbname = char(vbs{1});
end

fprintf('[read_ads_dataset] varblock: %s\n', vbname);
vb   = dset.get(vbname);
df   = vb.to_dataframe();

out.freq     = double(df.index.to_numpy());
out.freq_ghz = out.freq / 1e9;
out.points   = numel(out.freq);
out.varblock = vbname;
out.S = struct();
% 提取所有 S[i,j] 列
colnames = cell(df.columns.tolist());
for i = 1:numel(colnames)
    c = char(colnames{i});
    if startsWith(c, 'S[')
        fld = strrep(c, '[', '_');
        fld = strrep(fld, ']', '');
        fld = strrep(fld, ',', '_');
        out.S.(fld) = double(df.get(c).to_numpy());
    end
end
end
