function ok = ads_set_param(d, param_sets)
%ADS_SET_PARAM 设置 ADS 设计实例参数（MATLAB 直调 keysight.ads.de）。
%   ok = ADS_SET_PARAM(d, param_sets)
%
%   输入：
%     d          - de 打开的 Design 对象（ws.design('库:单元:视图') 返回）
%     param_sets - Nx3 cell：{实例名, 参数名, 值字符串}
%                  值带单位，如 {'TL2','L','5.087563 mm'}
%
%   输出：
%     ok - true 表示全部设置成功
%
%   示例：
%     [de,ds] = ads_init();
%     d = ws.design('python_lib:py_ms_lpf:schematic');
%     ads_set_param(d, {'TL2','L','5.087563 mm'; 'TL4','L','5.5 mm'});
%
%   依赖：先 ads_init() 建立 MATLAB->ADS Python 桥。

ok = false;
if nargin < 2 || size(param_sets,2) ~= 3
    return;                       % ok 保持 false
end
try
    for i = 1:size(param_sets,1)
        inst_name = char(param_sets{i,1});
        param_name = char(param_sets{i,2});
        value = char(param_sets{i,3});
        inst = d.find_instance(inst_name);
        % 先取 Param 对象到变量，再赋值（避免 py 集合的 () 索引赋值问题）
        pp = inst.parameters(param_name);
        pp.value = value;
        inst.update_item_annotation();
    end
catch ME
    fprintf(2, '设置参数失败: %s\n', ME.message);
    return;                       % ok 保持 false
end
ok = true;
end
