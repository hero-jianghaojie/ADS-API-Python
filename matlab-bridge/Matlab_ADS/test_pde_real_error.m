%% test_pde_real_error.m
% Directly import keysight.ads.de._pde and capture the real low-level error
clear; clc;
pyenv('Version', 'D:\Program Files\Keysight\ADS2025_Update2\tools\python\python.exe');
setenv('HPEESOF_DIR', 'D:\Program Files\Keysight\ADS2025_Update2');

% Manually run env setup (adds ADS bin to DLL search path)
setup = py.importlib.import_module('keysight.ads.de._extension_setup');
setup.setup_environment();
fprintf('setup_environment OK\n');

% Directly import _pde, capture real traceback
try
    pde = py.importlib.import_module('keysight.ads.de._pde');
    fprintf('OK: _pde imported\n');
    fprintf('repr: %s\n', char(string(pde)));
catch ME
    fprintf('FAIL importing _pde\n');
    fprintf('ME.message: %s\n', ME.message);
    % Use Python traceback module to print full stack
    tb = py.importlib.import_module('traceback');
    disp(tb.format_exc());
end

