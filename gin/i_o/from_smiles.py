"""
from_smiles.py

Operations for read smiles string.

MIT License

Copyright (c) 2019 Chodera lab // Memorial Sloan Kettering Cancer Center,
Weill Cornell Medical College, Nicea Research, and Authors

Authors:
Yuanqing Wang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""


# =============================================================================
# imports
# =============================================================================
# dependencies
import tensorflow as tf
# tf.enable_eager_execution()
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import multiprocessing
N_CPUS = multiprocessing.cpu_count()

# packages
from gin import molecule

# =============================================================================
# CONSTANTS
# =============================================================================
"""
ATOMS = [
    # common stuff,
    # w/ or w/o aromacity
    'C',
    'c',
    'N',
    'n',
    'O',
    'o',
    'S',
    's',

    # slightly uncommon
    'B',
    'b',
    'P',
    'p',

    # halogens
    'F',
    'Cl',
    'Br',

    # chiral stuff
    '[C@H]',
    '[C@@H]',

    # stuff with charges
    '[F-]',
    '[Cl-]',
    '[Br-]',
    '[Na+]',
    '[K+]',
    '[OH-]',
    '[NH4+]',
    '[H+]',

    # NOTE:
    # due to the consideration of speed, we don't support more exotic atoms
]
"""

ORGANIC_ATOMS = [
    'C',
    'c',
    'N',
    'n',
    'O',
    'o',
    'S',
    's',
    'P',
    'p',
    'F',
    'R', # Br
    'L', # Cl
    'I'
]

N_ORGANIC_ATOMS = len(ORGANIC_ATOMS)
ORGANIC_ATOMS_IDXS = list(range(N_ORGANIC_ATOMS))

TOPOLOGY_MARKS = [
    '=',
    '#',
    '\(',
    '\)',
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    '7',
    '8',
    '9',
]

ALL_TOPOLOGY_REGEX_STR = '|'.join(TOPOLOGY_MARKS)
ALL_ORGANIC_ATOMS_STR = '|'.join(ORGANIC_ATOMS)
N_ATOM_COUNTER_STR = '|'.join(
    TOPOLOGY_MARKS + [
    'l',
    'r',
    '\[',
    '\]',
    '@',
    'H',
    '\/',
    r'\\'
])

dummy_list = []

# =============================================================================
# utility functions
# =============================================================================
# @tf.function
def smiles_to_organic_topological_molecule(smiles):
    """ Decode a SMILES string to a molecule object.

    Organic atoms:
    [C, N, O, S, P, F, Cl, Br, I]

    Corresponding indices:
    [0, 1, 2, 3, 4, 5, 6, 7, 8]

    NOTE: to speed things up, this is the minimalistic function to
          parse a small molecule, with no flags and assertions whatsoever.
          we assume the validity of the smiles string.

    Parameters
    ----------
    smiles : str,
        smiles representation of a molecule.

    Returns
    -------
    molecule : molecule.Molecule object.
    """

    with tf.init_scope(): # register the variables
        # it is still eager environment here
        # we need to get:
        #     - number of atoms
        #     - number of brackets

        # strip it
        smiles = tf.strings.strip(smiles)

        # get the total length
        length = tf.strings.length(smiles)

        # get the number of atoms
        n_atoms = tf.cast(
            tf.strings.length(
                tf.strings.regex_replace(
                    smiles,
                    N_ATOM_COUNTER_STR,
                    '')),
            tf.int64)

    # initialize the adjacency map
    # the adjaceny map, by default,
    # (a.k.a. where no topology characters presented,)
    # should be an upper triangular matrix $A$,
    # with
    #
    # $$
    # A_{ij} = \begin{cases}
    # 1, i = j + 1;
    # 0, \mathtt{elsewhere}.
    # \end{cases}
    # $$
    #
    # for speed,
    # we achieve this by
    # deleting the first column and the last row
    # of an identity matrix with one more column & row

    # (n_atoms, n_atoms)
    adjacency_map = tf.Variable(
        lambda: tf.eye(
            n_atoms + 1,
            dtype=tf.float32)[1:, :-1]) # to enable aromatic bonds

    dummy_list.append(adjacency_map)


    # ==========================
    # get rid of the longer bits
    # ==========================
    # 'Br' to 'R'
    smiles = tf.strings.regex_replace(
        smiles, 'Br', 'R')

    # 'Cl' to 'L'
    smiles = tf.strings.regex_replace(
        smiles, 'Cl', 'L')

    # remove chiral stuff
    smiles = tf.strings.regex_replace(
        smiles, '\[C@H\]|\[C@@H\]|\[C@\]|\[C@@\]', 'C')

    smiles = tf.strings.regex_replace(
        smiles, '\[nH\]', 'n')

    smiles = tf.strings.regex_replace(
        smiles, '\/', '')

    smiles = tf.strings.regex_replace(
        smiles, r'\\', '')

    # get rid of all the topology chrs
    # in order to get the atoms
    smiles_atoms_only = tf.strings.regex_replace(
        smiles,
        ALL_TOPOLOGY_REGEX_STR,
        '')

    smiles_aromatic = tf.strings.regex_replace(
        smiles_atoms_only,
        'c|n|o|p',
        'A')

    # =================================
    # translate atoms notations to idxs
    # =================================
    # right now to depend on tf.strings to achieve this
    # TODO: further optimize this bit

    # carbon
    # aromatic or not
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'C|c',
        '0')

    # nitrogen
    # aromatic or not
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'N|n',
        '1')

    # oxygen
    # aromatic or not
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'O|o',
        '2')

    # sulfur
    # aromatic or not
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'S|s',
        '3')

    # phosphorus
    # aromatic or not
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'P|p', # NOTE: although not common, adding this doesn't hurt speed
        '4')

    # fluorine
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'F',
        '5')

    # chlorine
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'L',
        '6')

    # bromine
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'R',
        '7')

    # iodine
    smiles_atoms_only = tf.strings.regex_replace(
        smiles_atoms_only,
        'I',
        '8')

    # split it in order to convert to tf.Tensor with dtype=tf.int64
    atoms = tf.strings.bytes_split(
        smiles_atoms_only) # NOTE: add values here because this is suppose to be sparse


    atoms = tf.strings.to_number(
        atoms,
        tf.int64) # NOTE: int64 to be compatible


    # ==============================
    # handle the topology characters
    # ==============================
    smiles_topology_only = tf.strings.regex_replace(
        smiles,
        ALL_ORGANIC_ATOMS_STR,
        '0')

    # split it into array
    smiles_topology_only = tf.strings.bytes_split(
        smiles_topology_only)

    # find all the indices and characters indicating topology
    topology_idxs = tf.reshape(
        tf.where(
            tf.not_equal(
                smiles_topology_only,
                '0')),
        [-1])

    topology_chrs = tf.gather(
        smiles_topology_only,
        topology_idxs)


    # map the topology idxs onto the atoms
    # this is achieved by shifting the indices of the topology characters
    topology_idxs = topology_idxs\
        - tf.range(
            tf.cast(
                tf.shape(topology_idxs)[0],
                dtype=tf.int64),
            dtype=tf.int64)\
        - tf.constant(
            1,
            dtype=tf.int64)


    # ===========
    # bond orders
    # ===========
    #
    # NOTE: do this first allow us to tolerate the rings connected
    #       to multiple bonds
    # double bonds and triple bonds
    # modify the bond order to two or three
    double_bond_idxs = tf.gather(
        topology_idxs,
        tf.reshape(
            tf.where(
                tf.equal(
                    topology_chrs,
                    '=')),
            [-1]))

    triple_bond_idxs = tf.gather(
        topology_idxs,
        tf.reshape(
            tf.where(
                tf.equal(
                    topology_chrs,
                    '#')),
            [-1]))

    # update double bonds
    # (n_atoms, n_atoms)
    adjacency_map.scatter_nd_update(
        tf.transpose(
            tf.concat(
                [
                    tf.expand_dims(
                        double_bond_idxs,
                        0),
                    tf.expand_dims(
                        double_bond_idxs + 1,
                        0)
                ],
                axis=0)),
        tf.ones_like(
            double_bond_idxs,
            dtype=tf.float32) * 2)

    # update triple bonds
    # (n_atoms, n_atoms)
    adjacency_map.scatter_nd_update(
        tf.transpose(
            tf.concat(
                [
                    tf.expand_dims(
                        triple_bond_idxs,
                        0),
                tf.expand_dims(
                    triple_bond_idxs + 1,
                    0)
                ],
                axis=0)),
        tf.ones_like(
            triple_bond_idxs,
            dtype=tf.float32) * 3)

    # ========
    # branches
    # ========
    # side chains are marked with brackets.
    # two things happen when a pair of brackets is present
    # - the connection between the right bracket and the atom right to it
    #   is dropped
    # - a bond is formed between the right bracket and the atom left to the
    #   left bracket

    # init a queue
    bracket_queue = tf.constant([], dtype=tf.int64)

    # get a large matrix to record the pairs
    bracket_pairs = tf.constant(
        [[-1, -1]],
        tf.int64)

    first_right = tf.constant(True)
    def if_left(idx, bracket_queue, bracket_pairs):
        # if a certain position
        # it is a left bracket
        # put that bracket in the queue
        # NOTE: queue is not supported in graph
        # bracket_queue.enqueue(idx)
        bracket_queue = tf.concat(
            [
                bracket_queue,
                [idx]
            ],
            axis=0)

        return idx, bracket_queue, bracket_pairs

    def if_right(idx, bracket_queue, bracket_pairs,
            topology_idxs=topology_idxs):
        # if at a certain position
        # it is a right bracket
        # we need to do the following things
        #   - get a left bracket out of the queue
        #   - modify the adjacency matrix
        right_idx = topology_idxs[idx]
        left_idx = topology_idxs[bracket_queue[-1]]
        bracket_queue = bracket_queue[:-1]
        bracket_pairs = tf.concat(
            [
                bracket_pairs,
                tf.expand_dims(
                    [left_idx, right_idx],
                    axis=0)
            ],
            axis=0)

        return idx, bracket_queue, bracket_pairs

    def loop_body(idx, bracket_queue, bracket_pairs,
            topology_chrs=topology_chrs):
        # get the flag
        chr_flag = topology_chrs[idx]

        # if left
        idx, bracket_queue, bracket_pairs = tf.cond(
            tf.equal(
                chr_flag,
                '('),

            # if chr_flag == '('
            lambda: if_left(idx, bracket_queue, bracket_pairs),

            # else:
            lambda: (idx, bracket_queue, bracket_pairs))

        # if right
        idx, bracket_queue, bracket_pairs = tf.cond(
            tf.equal(
                chr_flag,
                ')'),

            # if chr_flag == '('
            lambda: if_right(idx, bracket_queue, bracket_pairs),

            # else:
            lambda: (idx, bracket_queue, bracket_pairs))

        # increment
        return idx+1, bracket_queue, bracket_pairs


    # while loop
    max_iter = tf.shape(topology_idxs)[0]
    idx = tf.constant(0)

    _, _, bracket_pairs = tf.while_loop(
        # condition
        lambda idx, _0, _1: tf.less(idx, max_iter),

        # body
        lambda idx, bracket_queue, bracket_pairs: \
            loop_body(idx, bracket_queue, bracket_pairs),

        # var
        [idx, bracket_queue, bracket_pairs],

        shape_invariants=[
            idx.get_shape(),
            tf.TensorShape([None, ]),
            tf.TensorShape([None, 2])])

    # get rid of the first row
    bracket_pairs = bracket_pairs[1:, ]

    # split into left and right brackets
    left_bracket_idxs = bracket_pairs[:, 0]
    right_bracket_idxs = bracket_pairs[:, 1]

    # we discard the right bracket at the end of the smiles string
    # because they don't mean anything
    right_bracket_idxs = tf.boolean_mask(
        right_bracket_idxs,
        tf.logical_not(
            tf.equal(
                right_bracket_idxs,
                n_atoms - 1)))

    left_bracket_idxs = left_bracket_idxs[:right_bracket_idxs.shape[0]]

    # handle the overlap between left and right brackets
    # as in
    # CCC(C)(C)CC
    left_right_overlaps = tf.where(
        tf.equal(
            tf.subtract(
                tf.tile(
                    tf.expand_dims(
                        left_bracket_idxs,
                        0),
                    [tf.shape(right_bracket_idxs)[0], 1]),
                tf.tile(
                    tf.expand_dims(
                        right_bracket_idxs,
                        1),
                    [1, tf.shape(right_bracket_idxs)[0]])),
            tf.constant(0, dtype=tf.int64)))

    def process_right_left_overlap(
            idx,
            left_bracket_idxs,
            right_bracket_idxs=right_bracket_idxs,
            left_right_overlaps=left_right_overlaps):

        left_right_overlap = left_right_overlaps[idx, :]

        left_bracket_idxs = tf.where(
            tf.equal(
                tf.range(
                    tf.shape(right_bracket_idxs, tf.int64)[0]),
                left_right_overlap[1]),
            tf.ones_like(left_bracket_idxs) \
                * left_bracket_idxs[left_right_overlap[0]],
            left_bracket_idxs)

        return idx + 1, left_bracket_idxs

    idx = tf.constant(0, dtype=tf.int64)


    _, left_bracket_idxs = tf.while_loop(
        lambda idx, _: \
            tf.less(idx, tf.shape(left_right_overlaps, tf.int64)[0]),
        process_right_left_overlap,
        [idx, left_bracket_idxs])

    current_bond_idxs = tf.transpose(
        tf.concat(
            [
                tf.expand_dims(
                    right_bracket_idxs,
                    0),
                tf.expand_dims(
                    right_bracket_idxs + 1,
                    0)
            ],
            axis=0))

    # get the current bond order
    current_bond_order = tf.gather_nd(
        adjacency_map,
        current_bond_idxs)

    # calculate where should the new bonds be
    new_bond_idxs = tf.transpose(
        tf.concat(
            [
                tf.expand_dims(
                    left_bracket_idxs,
                    0),
                tf.expand_dims(
                    right_bracket_idxs + 1,
                    0)
            ],
            axis=0))

    # drop the connection between right bracket and the atom right to it
    adjacency_map.scatter_nd_update(
        current_bond_idxs,
        tf.zeros_like(current_bond_order))

    # connect the atom right of the right bracket to the atom left of
    # the left bracket
    adjacency_map.scatter_nd_update(
        new_bond_idxs,
        current_bond_order)


    # =====
    # rings
    # =====
    #
    # NOTE: to speed things up,
    #       we allow a maximum of 5 rings in a molecule,
    #       this is already enough for the whole ZINC database
    #
    # when a digit appears in the SMILES string
    # a bond (single bond) is formed between
    # two labeled atoms

    # while loop
    idx = tf.constant(0, dtype=tf.int64)
    max_iter = tf.constant(5, dtype=tf.int64)
    connection_chrs = tf.constant([
        '1',
        '2',
        '3',
        '4',
        '5',
        '6'
    ], dtype=tf.string)

    # init bond indices and orders
    bond_idxs_to_update = tf.constant([[-1, -1]], dtype=tf.int64)
    bond_orders_to_update = tf.constant([-1], dtype=tf.float32)

    def loop_body(
            idx,
            bond_idxs_to_update,
            bond_orders_to_update,
            connection_chrs=connection_chrs):

        # get the connection character
        connection_chr = connection_chrs[idx]
        # search for this in the SMILES string
        # NOTE: we assume that there are two of them,
        #       again, unapologetically, we don't put any assertion here
        connection_idxs = tf.gather(
            topology_idxs,
            tf.reshape(
                tf.where(
                    tf.equal(
                        topology_chrs,
                        connection_chr)),
                [-1]))

        # handle the situation where there is more than one atoms connected
        # to the center
        connection_idxs = tf.sort(connection_idxs)

        # dirty stuff to get the permutations
        connection_idxs_x, connection_idxs_y = tf.meshgrid(
            connection_idxs,
            connection_idxs)

        connection_idxs_stack = tf.stack(
            [
                connection_idxs_x,
                connection_idxs_y
            ],
            axis=2)

        # count the number of connections
        n_connections = tf.shape(connection_idxs)[0]
        n_connections_bonds = tf.math.divide(
            n_connections * (n_connections - 1),
            2)

        tf.where(
                tf.equal(
                    tf.linalg.band_part(
                        tf.ones((n_connections, n_connections),
                            dtype=tf.int64),
                        0, -1),
                    tf.constant(0, dtype=tf.int64)))

        connection_idxs = tf.gather_nd(
            connection_idxs_stack,
            tf.where(
                    tf.equal(
                        tf.linalg.band_part(
                            tf.ones((n_connections, n_connections),
                                dtype=tf.int64),
                            0, -1),
                        tf.constant(0, dtype=tf.int64))))

        bond_idxs_to_update = tf.concat(
            [
                bond_idxs_to_update,
                connection_idxs,
            ],
            axis=0)

        bond_orders_to_update = tf.cond(
            tf.greater(
                tf.shape(connection_idxs)[0],
                0),

            lambda: tf.concat(
                [
                    bond_orders_to_update,
                    tf.ones(
                        (tf.shape(connection_idxs)[0], ),
                        dtype=tf.float32)
                ],
                axis=0),

            lambda: bond_orders_to_update)

        # increment
        return idx + 1, bond_idxs_to_update, bond_orders_to_update

    idx, bond_idxs_to_update, bond_orders_to_update = tf.case(
        [(
            tf.greater(
                tf.shape(topology_chrs)[0],
                0),

            lambda: tf.while_loop(
                lambda idx, _1, _2: tf.logical_and(
                    tf.less(idx, max_iter),
                    tf.logical_and(
                        tf.reduce_any(
                            tf.equal(
                                connection_chrs[idx],
                                topology_chrs)),
                        tf.greater(tf.shape(topology_chrs)[0], 0))),

                # loop body
                loop_body,

                # vars
                [idx, bond_idxs_to_update, bond_orders_to_update],

                shape_invariants=[
                    idx.get_shape(),
                    tf.TensorShape([None, 2]),
                    tf.TensorShape([None, ])],

                parallel_iterations=5)
        )],

        default=lambda: (idx, bond_idxs_to_update, bond_orders_to_update))

    # discard the first row
    bond_idxs_to_update = bond_idxs_to_update[1:, ]
    bond_orders_to_update = bond_orders_to_update[1:, ]


    adjacency_map.scatter_nd_update(
        bond_idxs_to_update,
        bond_orders_to_update)

    # ===========
    # aromaticity
    # ===========
    #
    # hard code aromaticity:
    #   where the aromatic atoms are coded as lower case letters
    # update the aromatic bond orders to half bonds
    smiles_aromatic = tf.strings.bytes_split(
        smiles_aromatic)

    # all the aromatic bonds where marked
    aromatic_idxs = tf.reshape(
        tf.where(
            tf.equal(
                smiles_aromatic,
                'A')),
        [-1])

    # we change the bond order of the aromatic atoms
    # to 1.5
    # now all the aromatic atoms should still be adjacent to each other
    aromatic_adjacency_map = tf.gather(
        tf.gather(
            adjacency_map,
            aromatic_idxs,
            axis=0),
        aromatic_idxs,
        axis=1)

    # dirty stuff to get the bond indices to update
    aromatic_idxs_x, aromatic_idxs_y = tf.meshgrid(
        tf.range(
            tf.cast(
                tf.shape(aromatic_idxs)[0],
                tf.int64),
            dtype=tf.int64),
        tf.range(
            tf.cast(
                tf.shape(aromatic_idxs)[0],
                tf.int64),
            dtype=tf.int64))

    aromatic_idxs_stack = tf.stack(
        [
            aromatic_idxs_x,
            aromatic_idxs_y
        ],
        axis=2)

    aromatic_idxs_2d = tf.boolean_mask(
        aromatic_idxs_stack,
        aromatic_adjacency_map)

    current_bond_idxs = tf.reverse(
        tf.reshape(
            tf.gather(
                aromatic_idxs,
                tf.reshape(
                    aromatic_idxs_2d,
                    [-1])),
            shape=tf.shape(aromatic_idxs_2d)),
        axis=[1])

    current_bond_order = tf.gather_nd(
        adjacency_map,
        current_bond_idxs)

    modified_bond_order = tf.where( # if
        tf.greater_equal(
            current_bond_order,
            tf.constant(1, dtype=tf.float32)),

        # if current_bond_order >= 1:
        current_bond_order + 0.5,

        # else:
        # if there is no bond right now, then we don't do anything
        current_bond_order)

    # update adjacency_map
    adjacency_map.scatter_nd_update(
        current_bond_idxs,
        modified_bond_order)

    # handle conjugate systems
    adjacency_map_full = adjacency_map + tf.transpose(adjacency_map)

    # =================
    # conjugate systems
    # =================
    # search start with atoms connected to double bonds
    sp2_idxs = tf.boolean_mask(
        tf.range(n_atoms,
            dtype=tf.int64),
        tf.reduce_any(
            tf.equal(
                adjacency_map_full,
                tf.constant(2.0, dtype=tf.float32)),
            axis=1))

    # also add aromatic idxs into our search
    sp2_idxs = tf.concat(
        [
            sp2_idxs,
            aromatic_idxs
        ],
        axis=0)

    # NOTE:
    # right now,
    # we only allow carbon, nitrogen, or oxygen
    # as part of our conjugate system
    sp2_idxs = tf.boolean_mask(
        sp2_idxs,
        tf.logical_or(

            tf.equal( # carbon
                tf.gather(atoms, sp2_idxs),
                tf.constant(
                    0,
                    dtype=tf.int64)),

            tf.logical_or(
                tf.equal( # nitrogen
                    tf.gather(atoms, sp2_idxs),
                    tf.constant(
                        1,
                        dtype=tf.int64)),

                tf.equal( # oxygen
                    tf.gather(atoms, sp2_idxs),
                    tf.constant(
                        2,
                        dtype=tf.int64)))))

    # gather only sp2 atoms
    sp2_adjacency_map = tf.gather(
        tf.gather(
            adjacency_map_full,
            sp2_idxs,
            axis=0),
        sp2_idxs,
        axis=1)

    # init conjugate_systems
    conjugate_systems = tf.expand_dims(
        tf.ones_like(sp2_idxs) \
            * tf.constant(-1, dtype=tf.int64),
        0)

    # init visited flags
    visited = tf.tile(
        tf.expand_dims(
            tf.constant(False),
            0),
        tf.expand_dims(
            tf.shape(sp2_idxs)[0],
            0))

    def loop_body_inner(queue, visited, conjugate_system,
            sp2_adjacency_map=sp2_adjacency_map):
        # dequeue
        idx = queue[-1]
        queue = queue[:-1]

        # flag the position of self
        is_self = tf.equal(
            tf.range(
                tf.cast(
                    tf.shape(sp2_adjacency_map)[0],
                    tf.int64),
                dtype=tf.int64),
            idx)

        # flag the neighbors
        is_neighbors = tf.greater(
            sp2_adjacency_map[idx, :],
            tf.constant(0, dtype=tf.float32))

        # flag the neighbors that are not visited
        is_unvisited_neighbors = tf.logical_and(
            is_neighbors,
            tf.logical_not(
                visited))

        # check if self is visited
        self_is_unvisited = tf.logical_not(visited[idx])

        # put self in the conjugate system if self is unvisited
        conjugate_system = tf.cond(
            self_is_unvisited,

            # if self.is_visited
            lambda: tf.concat( # put self into the conjugate_system
                [
                    conjugate_system,
                    tf.expand_dims(
                        idx,
                        0)
                ],
                axis=0),

            # else:
            lambda: conjugate_system)

        # get the states of the neighbors
        neighbors_unvisited = tf.boolean_mask(
            tf.range(
                tf.cast(
                    tf.shape(sp2_adjacency_map)[0],
                    tf.int64),
                dtype=tf.int64),
            is_unvisited_neighbors)

        # append the undiscovered neighbors to the conjugate system
        conjugate_system = tf.concat(
            [
                conjugate_system,
                neighbors_unvisited
            ],
            axis=0)

        # enqueue
        queue = tf.concat(
            [
                queue,
                neighbors_unvisited
            ],
            axis=0)

        # change the visited flag
        visited = tf.where(
            tf.logical_or(
                is_unvisited_neighbors,
                is_self),

            # if sp2_atom is neighbor and is unvisited:
            tf.tile(
                tf.expand_dims(
                    tf.constant(True),
                    0),
                tf.expand_dims(
                    tf.shape(is_unvisited_neighbors)[0],
                    0)),

            # else:
            visited)

        return queue, visited, conjugate_system

    def loop_body_outer(
            conjugate_systems,
            visited,
            sp2_adjacency_map=sp2_adjacency_map):

        # start with the first element that's not visited
        queue = tf.expand_dims(
            tf.boolean_mask(
                tf.range(
                    tf.cast(
                        tf.shape(sp2_adjacency_map)[0],
                        tf.int64),
                    dtype=tf.int64),
                tf.logical_not(visited))[0],
            0)

        # init conjugate system
        conjugate_system = tf.constant([], dtype=tf.int64)

        queue, visited, conjugate_system = tf.while_loop(
            # while len(queue) > 0:
            lambda queue, visited, conjugate_system: tf.greater(
                tf.shape(queue)[0],
                tf.constant(0, tf.int32)),

            # execute inner loop body
            loop_body_inner,

            # loop var
            [queue, visited, conjugate_system],

            shape_invariants=[
                tf.TensorShape([None, ]),
                tf.TensorShape(visited.get_shape()),
                tf.TensorShape([None, ])])

        conjugate_system = tf.cond(
            # check if there are at least three atoms in the conjugate system
            tf.greater_equal(
                tf.shape(conjugate_system)[0],
                tf.constant(3, dtype=tf.int32)),

            # if there is more than three atoms in the conjugate system:
            lambda: conjugate_system,

            # else:
            lambda: tf.constant([], dtype=tf.int64))

        # pad it with -1
        conjugate_system = tf.concat(
            [
                conjugate_system,
                tf.ones(tf.shape(sp2_idxs)[0] \
                    - tf.shape(conjugate_system)[0],
                    dtype=tf.int64) \
                    * tf.constant(-1, dtype=tf.int64)
            ],
            axis=0)

        # put conjugate system into the list of systems
        conjugate_systems = tf.concat(
            [
                conjugate_systems,
                tf.expand_dims(
                    conjugate_system,
                    0)
            ],
            axis=0)

        return conjugate_systems, visited

    conjugate_systems, visited = tf.while_loop(
        # while not all are visited
        lambda conjugate_systems, visited: tf.reduce_any(
            tf.logical_not(
                visited)),

        # loop_body
        loop_body_outer,

        # loop var
        [conjugate_systems, visited],

        shape_invariants=[
            tf.TensorShape([None, sp2_idxs.shape[0]]),
            tf.TensorShape((visited.get_shape()))])


    # get rid of the empty entries
    conjugate_systems = tf.boolean_mask(
        conjugate_systems,
        tf.reduce_any(
            tf.greater(
                conjugate_systems,
                tf.constant(-1, dtype=tf.int64)),
            axis=1))


    # while loop
    idx = tf.constant(0, dtype=tf.int32)
    bond_idxs_to_update = tf.constant([[-1, -1]], dtype=tf.int64)
    bond_orders_to_update = tf.constant([-1], dtype=tf.float32)

    # update the bond order according to conjugate_systems
    def loop_body(idx,
            bond_idxs_to_update,
            bond_orders_to_update,
            conjugate_systems=conjugate_systems,
            sp2_idxs=sp2_idxs,
            sp2_adjacency_map=sp2_adjacency_map):

        # get the conjugate system and get rid of the padding
        conjugate_system = conjugate_systems[idx, :]
        conjugate_system = tf.boolean_mask(
            conjugate_system,
            tf.greater(
                conjugate_system,
                tf.constant(-1, dtype=tf.int64)))

        # get the bonds in the system
        system_idxs = tf.gather(
            sp2_idxs,
            conjugate_system)

        # get the full adjacency map
        system_adjacency_map_full = tf.gather(
            tf.gather(
                sp2_adjacency_map,
                conjugate_system,
                axis=0),
            conjugate_system,
            axis=1),

        # flatten it to calculate average bond
        system_adjacency_map_flatten = tf.reshape(
            tf.linalg.band_part(
                system_adjacency_map_full,
                0, -1),
            [-1])

        # get the average bond order and count
        system_total_bond_order = tf.reduce_sum(system_adjacency_map_flatten)
        system_total_bond_count = tf.reduce_sum(
            tf.boolean_mask(
                tf.ones_like(
                    system_adjacency_map_flatten,
                    dtype=tf.float32),
                tf.greater(
                    system_adjacency_map_flatten,
                    tf.constant(0, dtype=tf.float32))))

        system_mean_bond_order = tf.math.divide(
            system_total_bond_order,
            system_total_bond_count)

        # dirty stuff to get the bond indices to update
        all_idxs_x, all_idxs_y = tf.meshgrid(
            tf.range(n_atoms, dtype=tf.int64),
            tf.range(n_atoms, dtype=tf.int64))

        all_idxs_stack = tf.stack(
            [
                all_idxs_y,
                all_idxs_x
            ],
            axis=2)

        system_idxs_2d = tf.gather(
            tf.gather(
                all_idxs_stack,
                system_idxs,
                axis=0),
            system_idxs,
            axis=1)

        system_idxs_2d = tf.boolean_mask(
            system_idxs_2d,
            tf.greater(
                tf.gather_nd(
                    adjacency_map,
                    system_idxs_2d),
                tf.constant(0, dtype=tf.float32)))

        bond_idxs_to_update = tf.concat(
            [
                bond_idxs_to_update,
                system_idxs_2d
            ],
            axis=0)

        bond_orders_to_update = tf.concat(
            [
                bond_orders_to_update,
                tf.ones(
                    (tf.cast(system_total_bond_count, tf.int32), ),
                    dtype=tf.float32) \
                    * system_mean_bond_order
            ],
            axis=0)

        return idx + 1, bond_idxs_to_update, bond_orders_to_update

    _, bond_idxs_to_update, bond_orders_to_update = tf.while_loop(
        # condition
        lambda idx, _1, _2: tf.less(
            idx,
            tf.shape(conjugate_systems)[0]),

        # loop body
        loop_body,

        # var
        [idx, bond_idxs_to_update, bond_orders_to_update],

        shape_invariants = [
            idx.get_shape(),
            tf.TensorShape([None, 2]),
            tf.TensorShape([None, ])])

    # get rid of the placeholder
    bond_idxs_to_update = bond_idxs_to_update[1:]
    bond_orders_to_update = bond_orders_to_update[1:]

    # scatter update
    adjacency_map.scatter_nd_update(
        bond_idxs_to_update,
        bond_orders_to_update)

    return atoms, adjacency_map.read_value()

def to_mol(
        smiles,
        chiral=False):
    """ Wrapper function for translating one SMILES string to molecule.
    """
    if chiral == False:
        mol = smiles_to_organic_topological_molecule(smiles)

    else:
        return NotImplementedError

    return mol


def to_mols(
        smiles_array,
        chiral=False): # TODO: chiral is unused
    """ Wrapper function for translating multiple SMILES strings to molecules.
    """
    # put the smiles into a large tensor
    smiles_array = tf.convert_to_tensor(smiles_array, dtype=tf.string)

    ds_smiles = tf.data.Dataset.from_tensor_slices(smiles_array)

    ds = ds_smiles.map(lambda x: tf.py_function(
        to_mol,
        [x],
        [tf.int64, tf.float32]))

    return ds

def to_mols_with_attributes(
        smiles_array,
        attributes_array,
        chiral=False):
    """ Wrapper function for translating multiple SMILES strings to molecules.
    """
    # put the smiles into a large tensor
    smiles_array = tf.convert_to_tensor(smiles_array, dtype=tf.string)
    attributes_array = tf.convert_to_tensor(attributes_array, dtype=tf.float32)

    ds = tf.data.Dataset.from_tensor_slices((smiles_array, attributes_array))

    ds = ds.map(lambda x, y: tf.py_function(
        lambda x,y: (to_mol(x)[0], to_mol(x)[1], y),
        [x, y],
        [tf.int64, tf.float32, tf.float32]))

    return ds
