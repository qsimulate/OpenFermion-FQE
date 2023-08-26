#   Copyright 2020 Google LLC

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
Global settings for FQE.
"""
from enum import Flag


class CodePath(Flag):
    """
    Enum for available code paths.
    """
    C = True
    PYTHON = False


available_code_paths = (CodePath.PYTHON, CodePath.C)
"""
Tuple providing information about the availability of the
C and Python codepaths, depending on the setup/compilation
options. For now, it provides both paths but when conditional
compilation of the code is enabled, this tuple should reflect
the available code paths.
"""

use_accelerated_code = CodePath.C in available_code_paths
"""
A switch to check if accelerated code is used. Default is true if accelerated code is available
"""

global_max_norb = 64
"""
The global maximum number of orbitals that can be handled by FQE.
"""

c_string_max_norb = 63
"""
The max number of orbitals correctly handled by the C codepath
for generating determinant strings.
"""
