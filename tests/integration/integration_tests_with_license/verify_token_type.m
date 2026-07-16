% Copyright 2026 The MathWorks, Inc.
%
% verify_token_type - Verify the type of access token used to start MATLAB.
%
% This script queries the MathWorks authentication service to determine the
% token type (e.g., MWAS or MWAJ) associated with the current MATLAB session.
%
% When MWI_ENABLE_LONG_RUNNING_SESSION is set, the token type should be MWAJ.
% Otherwise, the default token type is MWAS.
%
% Output:
%   Prints "Token Type: <type>" to stdout, where <type> is the
%   loginIdentifierType returned by the authentication service.

% Retrieve the current session identity token from the environment variable
token = getenv('MLM_WEB_USER_CRED');

% Query the MathWorks authentication service to inspect the token
wsEnv = getenv('WS_ENV');
if isempty(wsEnv) || strcmp(wsEnv, 'production')
    authUrl = 'https://login.mathworks.com/authenticationws/service/v4/tokens';
else
    authUrl = sprintf('https://login-%s.mathworks.com/authenticationws/service/v4/tokens', wsEnv);
end

payload = struct('tokenString', token, 'tokenPolicyName', 'L1');
jsonBody = jsonencode(payload);

options = weboptions( ...
    'MediaType', 'application/json', ...
    'HeaderFields', { ...
        'accept', 'application/json'; ...
        'x_mw_ws_callerid', 'desktop-jupyter' ...
    }, ...
    'RequestMethod', 'post', ...
    'Timeout', 30 ...
);

response = webwrite(authUrl, jsonBody, options);

fprintf('Token Type: %s', response.loginIdentifierType);
