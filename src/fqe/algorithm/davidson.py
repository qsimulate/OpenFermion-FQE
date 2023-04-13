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
"""Reference implementation of Davidson-Liu diagonalization with numpy and FQE.
"""
from itertools import product
import copy
import time

import numpy as np

import fqe
from fqe import util
from fqe.hamiltonians.hamiltonian import Hamiltonian


class ConvergenceError(Exception):
    """Error for failed convergence in Davidson-Liu diagonalization."""
    pass


def davidsonliu(
        hmat: np.ndarray,
        nroots: int,
        guess_vecs=None,
        epsilon: float = 1.0e-8,
        verbose=False,
):
    """TODO: Add docstring."""
    # check if the nroots is specified correctly
    if nroots < 1 or nroots > hmat.shape[0] // 2:
        raise ValueError("Number of roots is incorrectly specified")
    dim = hmat.shape[0]

    # initialize the guess vectors if None
    if guess_vecs is None:
        guess_vecs = []
        for idx in range(nroots * 2):
            tmp_gv = np.zeros((dim, 1))
            tmp_gv[idx, 0] = 1
            guess_vecs.append(tmp_gv)

    old_thetas = np.array([np.infty] * nroots)
    hmat_diag = np.diagonal(hmat)
    while len(guess_vecs) <= dim:
        if verbose:
            print()
        current_num_gv = len(guess_vecs)

        # build subspace matrices
        # this can easily be improved to linear scaling with |guess_ves|
        # by storing the intermediate subspace matrix instead of rebuilding
        start_time = time.time()
        subspace_mat = np.zeros((len(guess_vecs), len(guess_vecs)),
                                dtype=np.complex128)
        for i, j in product(range(len(guess_vecs)), repeat=2):
            if i >= j:
                val = guess_vecs[i].T @ hmat @ guess_vecs[j]
                if isinstance(val, (float, complex, np.complex128, np.complex)):
                    subspace_mat[i, j] = val
                else:
                    subspace_mat[i, j] = val[0, 0]
                subspace_mat[j, i] = subspace_mat[i, j].conj()
        if verbose:
            print("subspace mat problem formation ", time.time() - start_time)

        # for nroots residuals
        start_time = time.time()
        w, v = np.linalg.eigh(subspace_mat)
        if verbose:
            print("subspace eig problem time: ", time.time() - start_time)

        # if converged return
        if verbose:
            print(
                "eig convergence  {}, ".format(
                    np.linalg.norm(w[:nroots] - old_thetas)),
                w[:nroots] - old_thetas,
            )
        if np.linalg.norm(w[:nroots] - old_thetas) < epsilon:

            # build eigenvectors
            eigenvectors = []
            for i in range(nroots):
                eigenvectors.append(
                    sum([
                        v[j, i] * guess_vecs[j] for j in range(current_num_gv)
                    ]))

            return w[:nroots], eigenvectors

        # else set new roots to the old roots
        old_thetas = w[:nroots]
        if verbose:
            print(old_thetas)

        # update the subspace vecs with the vecs of the subspace problem with
        # the nroots lowest eigenvalues
        for i in range(nroots):
            start_time = time.time()
            # expand in the space of all existing guess_vecs
            subspace_eigvec_expanded = sum(
                [v[j, i] * guess_vecs[j] for j in range(current_num_gv)])

            residual = (hmat @ subspace_eigvec_expanded -
                        w[i] * subspace_eigvec_expanded)
            # this is wrong. preconditioner is w[i] - np.diag(hmat)
            preconditioned_residual = np.multiply(
                residual.flatten(), np.reciprocal(w[i] - hmat_diag)).reshape(
                    (-1, 1))
            if verbose:
                print("residual formation time ", time.time() - start_time)

            start_time = time.time()
            overlaps = []
            for idx in range(len(guess_vecs)):
                overlaps.append(
                    guess_vecs[idx].conj().T @ preconditioned_residual)
            for idx in range(len(guess_vecs)):
                preconditioned_residual -= overlaps[idx] * guess_vecs[idx]
            if verbose:
                print("orthogonalization time ", time.time() - start_time)
            # normalize and add to guess_vecs
            guess_vecs.append(preconditioned_residual /
                              np.linalg.norm(preconditioned_residual))

    raise ConvergenceError("Maximal number of steps exceeded")


def davidsonliu_fqe(
        hmat: Hamiltonian,
        nroots: int,
        guess_vecs,
        nele,
        sz,
        norb,
        epsilon: float = 1.0e-8,
        verbose=False,
):
    """TODO: Add docstring."""
    if nroots < 1 or nroots > 2**(hmat.dim() - 1):
        raise ValueError("Number of roots is incorrectly specified")

    gv_sector = list(guess_vecs[0].sectors())[0]
    for gv in guess_vecs:
        if list(gv.sectors())[0] != gv_sector:
            raise TypeError("Sectors don't match for guess vectors")

    # get diagonal Hamiltonian as the preconditioner.
    # TODO: This should be changed to Slater-Condon rules construction and not
    #  this hack!
    diagonal_ham = np.zeros_like(guess_vecs[0].sector(gv_sector).coeff)
    graph = guess_vecs[0].sector(gv_sector).get_fcigraph()
    empty_vec = np.zeros_like(diagonal_ham)
    comp_basis = fqe.Wavefunction([[nele, sz, norb]])
    old_ia, old_ib = None, None

    for ia in graph.string_alpha_all():
        for ib in graph.string_beta_all():
            # empty_vec = np.zeros_like(diagonal_ham)
            if old_ia is not None and old_ib is not None:
                empty_vec[old_ia, old_ib] = 0.0
            empty_vec[graph.index_alpha(ia), graph.index_beta(ib)] = 1.0
            assert np.isclose(np.sum(empty_vec), 1)
            old_ia, old_ib = graph.index_alpha(ia), graph.index_beta(ib)
            comp_basis.set_wfn(strategy="from_data",
                               raw_data={(nele, sz): empty_vec})
            diagonal_ham[graph.index_alpha(ia),
                         graph.index_beta(ib)] = comp_basis.expectationValue(
                             hmat).real

    old_thetas = np.array([np.infty] * nroots)

    # Orthogonalize guess_vecs
    unortho_guess_vecs = guess_vecs
    guess_vecs = []
    for f_k in unortho_guess_vecs:
        # orthogonalize preconditioned_residual
        overlaps = []
        for idx in range(len(guess_vecs)):
            overlaps.append(
                np.sum(
                    np.multiply(
                        guess_vecs[idx].get_coeff(gv_sector),
                        f_k.get_coeff(gv_sector),
                    )))

        for idx in range(len(guess_vecs)):
            f_k.sector(gv_sector).coeff -= \
                overlaps[idx] * guess_vecs[idx].sector(gv_sector).coeff
        f_k.normalize()
        guess_vecs.append(f_k)

    while len(guess_vecs) <= graph.lena() * graph.lenb():
        if verbose:
            print()
        current_num_gv = len(guess_vecs)
        start_time = time.time()
        subspace_mat = np.zeros((len(guess_vecs), len(guess_vecs)),
                                dtype=np.complex128)
        for i, j in product(range(len(guess_vecs)), repeat=2):
            if i >= j:
                assert abs(guess_vecs[j].norm() - 1.) < 1e-8
                subspace_mat[i, j] = guess_vecs[j].expectationValue(
                    hmat, brawfn=guess_vecs[i])
                subspace_mat[j, i] = subspace_mat[i, j].conj()
        if verbose:
            print("subspace mat problem formation ", time.time() - start_time)

        # for nroots residuals
        start_time = time.time()
        w, v = np.linalg.eigh(subspace_mat)
        if verbose:
            print("subspace eig problem time: ", time.time() - start_time)

        # if converged return
        if verbose:
            print(
                "eig convergence  {}, ".format(
                    np.linalg.norm(w[:nroots] - old_thetas)),
                w[:nroots] - old_thetas,
            )
        if np.linalg.norm(w[:nroots] - old_thetas) < epsilon:
            # build eigenvectors
            eigenvectors = []
            for i in range(nroots):
                eigenvectors.append(
                    sum([
                        v[j, i] * guess_vecs[j].sector(gv_sector).coeff
                        for j in range(current_num_gv)
                    ]))
            eigfuncs = []
            for eg in eigenvectors:
                new_wfn = copy.deepcopy(guess_vecs[0])
                new_wfn.set_wfn(strategy='from_data', raw_data={gv_sector: eg})
                eigfuncs.append(new_wfn)

            return w[:nroots], eigfuncs

        # else set new roots to the old roots
        old_thetas = w[:nroots]
        if verbose:
            print("Old Thetas: ", old_thetas)
        # update the subspace vecs with the vecs of the subspace problem with
        # the nroots lowest eigenvalues
        for i in range(nroots):
            # expand in the space of all existing guess_vecs
            subspace_eigvec_expanded = sum([
                v[j, i] * guess_vecs[j].sector(gv_sector).coeff
                for j in range(current_num_gv)
            ])
            subspace_eigvec = copy.deepcopy(guess_vecs[0])
            subspace_eigvec.set_wfn(
                strategy="from_data",
                raw_data={gv_sector: subspace_eigvec_expanded},
            )
            # this should return a fresh wavefunction copy.deepcop
            residual = subspace_eigvec.apply(hmat)
            subspace_eigvec.scale(-w[i])
            residual = residual + subspace_eigvec

            preconditioner = copy.deepcopy(residual)
            preconditioner.set_wfn(
                strategy="from_data",
                raw_data={gv_sector: np.reciprocal(w[i] - diagonal_ham)},
            )
            f_k_coeffs = np.multiply(
                preconditioner.sector(gv_sector).coeff,
                residual.sector(gv_sector).coeff,
            )
            f_k = copy.deepcopy(residual)
            f_k.set_wfn(strategy="from_data", raw_data={gv_sector: f_k_coeffs})

            # orthogonalize preconditioned_residual
            overlaps = [util.vdot(v, f_k) for v in guess_vecs]

            for idx in range(len(guess_vecs)):
                f_k.sector(gv_sector).coeff -= \
                    overlaps[idx] * guess_vecs[idx].sector(gv_sector).coeff

            f_k.normalize()
            guess_vecs.append(f_k)

    eigenvectors = []
    for i in range(nroots):
        eigenvectors.append(
            sum([
                v[j, i] * guess_vecs[j].sector(gv_sector).coeff
                for j in range(current_num_gv)
            ]))
    eigfuncs = []
    for eg in eigenvectors:
        new_wfn = copy.deepcopy(guess_vecs[0])
        new_wfn.set_wfn(strategy='from_data', raw_data={gv_sector: eg})
        eigfuncs.append(new_wfn)

    return w[:nroots], eigfuncs


def davidson_diagonalization(
        hamiltonian: fqe.restricted_hamiltonian.RestrictedHamiltonian,
        n_alpha: int,
        n_beta: int,
        nroots=1,
        guess_vecs=None):
    norb = hamiltonian.dim()  # this should be the num_orbitals
    if not isinstance(hamiltonian, fqe.restricted_hamiltonian.RestrictedHamiltonian):
        norb //= 2
    nele = n_alpha + n_beta
    sz = n_alpha - n_beta
    wfn = fqe.Wavefunction([[nele, sz, norb]])
    graph = wfn.sector((nele, sz)).get_fcigraph()

    # Generate Guess Vecs for Davidson-Liu
    if guess_vecs is None:
        guess_vec1_coeffs = np.zeros((graph.lena(), graph.lenb()),
                                     dtype=np.complex128)
        guess_vec2_coeffs = np.zeros((graph.lena(), graph.lenb()),
                                     dtype=np.complex128)
        alpha_hf = fqe.util.init_bitstring_groundstate(n_alpha)
        beta_hf = fqe.util.init_bitstring_groundstate(n_beta)
        guess_vec1_coeffs[graph.index_alpha(alpha_hf),
                          graph.index_beta(beta_hf)] = 1.0
        guess_vec2_coeffs[graph.index_alpha(alpha_hf << 1),
                          graph.index_beta(beta_hf << 1)] = 1.0

        guess_wfn1 = copy.deepcopy(wfn)
        guess_wfn2 = copy.deepcopy(wfn)
        guess_wfn1.set_wfn(
            strategy="from_data",
            raw_data={(nele, sz): guess_vec1_coeffs},
        )
        guess_wfn2.set_wfn(
            strategy="from_data",
            raw_data={(nele, sz): guess_vec2_coeffs},
        )
        fqe_random = fqe.Wavefunction([[nele, sz, norb]])
        fqe_random.set_wfn(strategy='random')
        fqe_random.normalize()
        # Bad convergence this way
        guess_vecs = [guess_wfn1, guess_wfn2, fqe_random]
        # guess_vecs = [guess_wfn1, guess_wfn2]

    # run FQE-DL
    dl_w, dl_v = davidsonliu_fqe(hamiltonian,
                                 nroots,
                                 guess_vecs,
                                 nele=nele,
                                 sz=sz,
                                 norb=norb)
    return dl_w, dl_v
