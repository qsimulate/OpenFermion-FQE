#include "cirq_utils.h"

#include <complex.h>
#include <stdlib.h>
#include <omp.h>

#include "bitstring.h"
#include "macros.h"

/* C-kernel for detecting the non-empty sectors in a cirq wfn.
 *
 * This should work for any linear encoder. The encoding part is taken into
 * account by the python code and is passed to this kernel through `cirq_aids`
 * and `cirq_bids`.
 */
void detect_cirq_sectors(double complex * cirq_wfn,
                         double thresh,
                         int * paramarray,
                         const int norb,
                         const int alpha_states,
                         const int beta_states,
                         const long long * cirq_aids,
                         const long long * cirq_bids,
                         const int * anumb,
                         const int * bnumb
                         )
{
  const int param_leading_dim = 2 * norb + 1;
#pragma omp parallel for schedule(static)
  for (int alpha_id = 0; alpha_id < alpha_states; ++alpha_id) {
    const long long cirq_aid = cirq_aids[alpha_id];
    const int alpha_num = anumb[alpha_id];

    for (int beta_id = 0; beta_id < beta_states; ++beta_id) {
      // For a linear encoder (mod 2) this should work.
      const long long cirq_id = cirq_aid ^ cirq_bids[beta_id];
      if (cabs(cirq_wfn[cirq_id]) < thresh) { continue; }

      const int beta_num = bnumb[beta_id];
      const int pnum = alpha_num + beta_num;
      const int sz_shift = alpha_num - beta_num + norb;

      // Not entirely sure if race condition is OK here.
      paramarray[pnum * param_leading_dim + sz_shift] = 1;
    }
  }
}