/*
    Copyright 2021 Google LLC

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
*/

#ifndef SRC_FQE_LIB_CIRQ_UTILS_H_
#define SRC_FQE_LIB_CIRQ_UTILS_H_

#include <complex.h>

void detect_cirq_sectors(double complex * cirq_wfn,
                         double thresh,
                         int * paramarray,
                         const int norb,
                         const int alpha_states,
                         const int beta_states,
                         const long long * cirq_aids,
                         const long long * cirq_bids,
                         const int * anumb,
                         const int * bnumb);

#endif  // SRC_FQE_LIB_CIRQ_UTILS_H_
