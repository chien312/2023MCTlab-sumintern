import numpy as np
import time
from itertools import chain, combinations, takewhile
import matplotlib.pyplot as plt
from collections import Counter


def cardinality_score(p, q):
    '''Calculate Cardinality Score'''
    set_p = set(p)
    set_q = set(q)
    return len(set_p & set_q) / max(len(set_p), len(set_q))


def get_vTable(notes):
    '''Calculate the vector table'''

    ftype = np.float16
    itype = np.int32
    dt = [
        ('ioi', ftype),
        ('ipi', itype),
        ('isi', ftype),
        ('is_same_staff', np.bool),
        ('start', np.uint32),
        ('end', np.uint32)
    ] # data type

    # Pairwise comparisons
    n_notes = len(notes) # number of notes
    ioi = notes['onset'][None, :] - notes['onset'][:, None] # inter-onset interval
    ipi = notes['pitch'][None, :] - notes['pitch'][:, None] # inter-pitch interval
    isi = notes['onset'][None, :] - (notes['onset'] + notes['duration'])[:, None] # inter-sound interval
    is_same_staff = (notes['staff'][None, :] == notes['staff'][:, None]) # is the same staff
    grid = np.indices((n_notes, n_notes)) # an array representing the indices of a grid
    fromPoint = grid[0] # row indices, start points of vectors
    toPoint = grid[1] # column indices, end points of vectors

    # Convert vTable into structured array
    vTable = np.core.records.fromarrays([ioi, ipi, isi, is_same_staff, fromPoint, toPoint], dtype=dt)
    return vTable


PN = np.array(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'])
PN_f = np.array(['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'])



def plot_pattern(pattern, notes, ax, show=True):# draw pattern
    points = [[notes[p]['onset'], notes[p]['onset'] + notes[p]['duration'], notes[p]['pitch']] for p in pattern] # [onset, end, pitch]
    plt.tick_params(axis='both', which='major', labelsize=7)
    plt.xlabel("Crotchet Beat", fontsize=8)  # Label of X-Axis
    plt.ylabel("Pitch", fontsize=8)  # Label of Y-Axis
    for i in range(len(points)):
        plt.hlines(points[i][2], points[i][0], points[i][1], colors='g', lw=3)
        ax.annotate(PN[points[i][2] % 12], (points[i][0], points[i][2]+0.1), size=7)
    if show:
        plt.show()


def find_motives(notes, horizontalTolerance=0, verticalTolerance=3, adjacentTolerance=(2, 12),
                 min_notes=4, min_cardinality=0.8):
    '''Find translatable patterns'''

    def check_adjacency(context, check_vertical=False):
        # check adjacency constraint on context
        if len(context) > 0:
            pre = context[:-1]
            post = context[1:]

            ioi = vTable['ioi'][pre, post]
            ipi = vTable['ipi'][pre, post]

            if check_vertical:
                ioi_invalid = ioi > adjacentTolerance[0]
                ipi_invalid = np.abs(ipi) > adjacentTolerance[1]
                invalid_ids = np.where(ioi_invalid | ipi_invalid)[0]
            else:
                ioi_invalid = ioi > adjacentTolerance[0]
                invalid_ids = np.where(ioi_invalid)[0]
            if invalid_ids.size > 0:
                context = context[:invalid_ids[0]] # remove invalid notes
        return context

    def melodic(context):
        context = check_adjacency(context)
        invalid = None
        for i, j in zip(context[:-1], context[1:]):
            if len(
                    [k for k in range(i+1, j)
                     if (notes['pitch'][k] - notes['pitch'][i]) * (notes['pitch'][j] - notes['pitch'][k]) >= 0]
            ):
                invalid = i
                break
        return context[:context.index(invalid)+1] if invalid is not None else context

    def match_context(a, b, a_context, b_context):
        # get matching part (cotext) between two contexts
        a_context = np.array(a_context)
        b_context = np.array(b_context)

        # Forward comparison
        ioi_comparison = np.abs(vTable['ioi'][a, a_context][:, None] - vTable['ioi'][b, b_context][None, :])
        ipi_comparison = np.abs(vTable['ipi'][a, a_context][:, None] - vTable['ipi'][b, b_context][None, :])

        ipi_sign_a = np.sign(vTable['ipi'][a, a_context])[:, None]
        ipi_sign_b = np.sign(vTable['ipi'][b, b_context])[None, :]
        ipi_sign_mask = ((ipi_sign_a * ipi_sign_b) == 0) | np.equal(ipi_sign_a, ipi_sign_b)

        comparison_mask = (ioi_comparison <= horizontalTolerance) & \
                          (ipi_comparison <= verticalTolerance) & \
                          ipi_sign_mask

        # Extract matching part of the two contexts
        # a_mask = np.any(comparison_mask, axis=1)
        # b_mask = np.any(comparison_mask, axis=0)
        # print(a_mask, b_mask)

        ipi_comparison[comparison_mask==False] = 99
        a_pointer = b_pointer = 0
        a_mask, b_mask = [], []
        for ipi_col, comp_col in zip(ipi_comparison.T, comparison_mask.T):
            if comp_col[a_pointer:].any():
                idx = a_pointer + np.argmin(ipi_col[a_pointer:])
                a_mask.append(idx)
                a_pointer = idx + 1
        for ipi_row, comp_row in zip(ipi_comparison, comparison_mask):
            if comp_row[b_pointer:].any():
                idx = b_pointer + np.argmin(ipi_row[b_pointer:])
                b_mask.append(idx)
                b_pointer = idx + 1

        a_cotext = a_context[a_mask]
        b_cotext = b_context[b_mask]

        # if a_mask.sum() < min_notes - 1 or b_mask.sum() < min_notes - 1:
        #     return [np.array([]), np.array([])] # return empty array
        #
        # if a_mask.sum() != b_mask.sum():
        #     # Remove invalid concurrent notes
        #     rows, cols = comparison_mask.shape
        #     a_concurrences = [
        #         ((i, j), (i + 1, j)) for j, col in enumerate(comparison_mask.T) if col.sum() > 1
        #         for i in range(rows - 1) if col[i] and col[i + 1]
        #     ]
        #     b_concurrences = [
        #         ((i, j), (i, j + 1)) for i, row in enumerate(comparison_mask) if row.sum() > 1
        #         for j in range(cols - 1) if row[j] and row[j + 1]
        #     ]
        #
        #     concurrences = a_concurrences + b_concurrences
        #     if len(concurrences) > 0:
        #         invalids = [
        #             idx for concurrence in concurrences for idx in concurrence
        #             if idx != min(concurrence, key=lambda id: ipi_comparison[id])
        #         ]
        #
        #     for id in invalids:
        #         comparison_mask[id] = False
        #
        # a_cotext = a_context[np.any(comparison_mask, axis=1)]
        # b_cotext = b_context[np.any(comparison_mask, axis=0)]

        # # SSM comparison
        # assert a_cotext.size == b_cotext.size
        # a_pattern, b_pattern = np.insert(a_cotext, 0, a), np.insert(b_cotext, 0, b)
        # ioi_SSM_comparison = np.abs(vTable['ioi'][a_pattern][:, a_pattern] - vTable['ioi'][b_pattern][:, b_pattern])
        # ipi_SSM_comparison = np.abs(vTable['ipi'][a_pattern][:, a_pattern] - vTable['ipi'][b_pattern][:, b_pattern])
        #
        # ipi_sign_SSM_a = np.sign(vTable['ipi'][a_pattern][:, a_pattern])
        # ipi_sign_SSM_b = np.sign(vTable['ipi'][b_pattern][:, b_pattern])
        # ipi_sign_SSM_mask = ((ipi_sign_SSM_a * ipi_sign_SSM_b) == 0) | np.equal(ipi_sign_SSM_a, ipi_sign_SSM_b)
        #
        # SSM_comparison_mask = (ioi_SSM_comparison <= horizontalTolerance) & \
        #                       (ipi_SSM_comparison <= verticalTolerance) & \
        #                       ipi_sign_SSM_mask
        #
        # negative_groups = {} # incompatible groups
        # for i, row in enumerate(SSM_comparison_mask):
        #     if row.sum() != row.size:
        #         key = tuple(row)
        #         if key not in negative_groups.keys():
        #             negative_groups[key] = []
        #         negative_groups[key].append(i)
        #
        # invalids = []
        # if len(negative_groups.keys()) > 0:
        #     while len(negative_groups.keys()) > 1:
        #         key, invalid = min(negative_groups.items(), key=lambda item: len(item[1]))
        #         invalids.extend(invalid)
        #         negative_groups.pop(key)
        #
        # pattern_mask = np.ones_like(a_pattern, dtype=np.bool)
        # pattern_mask[invalids] = False
        #
        # a_pattern = a_pattern[pattern_mask]
        # b_pattern = b_pattern[pattern_mask]

        a_pattern = [a] + list(a_cotext)
        b_pattern = [b] + list(b_cotext)
        a_pattern = melodic(list(a_pattern))
        b_pattern = melodic(list(b_pattern))
        return [a_pattern, b_pattern]

    def melodic_check(context):
        # et = time.time()
        # print('context', context)
        if len(set(notes['onset'][context])) < len(context):
            # simultaneous notes
            # print('simultaneous %.4f' % (time.time() - et))
            # et = time.time()
            # print('simultaneous notes')
            return False

        # if np.any(notes['onset'][context[1:]] - notes['onset'][context[:-1]] - notes['duration'][context[:-1]] > adjacentTolerance[0]):
        #     # isi violation
        #     # print('isi %.4f' % (time.time() - et))
        #     # et = time.time()
        #     # print('isi violation')
        #     return False

        # for i, j in zip(context[:-1], context[1:]):
        #     if len(
        #             [k for k in range(i+1, j)
        #              if (notes['pitch'][k] - notes['pitch'][i]) * (notes['pitch'][j] - notes['pitch'][k]) >= 0]
        #     ):
        #         # melodic violation
        #         # print('mel %.4f' % (time.time() - et))
        #         # print('melodic violation')
        #         return False
        return True
    # temp = [5, 15, 23, 24, 25, 26, 32]
    # print(melodic_check(temp))
    # print(notes[['pitch', 'onset']][[5, 9, 10, 11, 15]])
    # exit()

    n_notes = notes.shape[0] # number of notes
    print('number of unique notes =', n_notes)

    # Get vector table
    clkStart = time.time()
    vTable = get_vTable(notes)
    print('Elapsed time (get vTable) = %.2f sec' % (time.time() - clkStart))
    clkStart = time.time()

    # Get context of each note
    n_context = 12 # in crochet beats
    context_dict = {}
    for i in range(n_notes):
        cond = (vTable['ioi'][i] < n_context) & (vTable['end'][i] > i) & vTable['is_same_staff'][i]
        i_context = list(vTable['end'][i][cond])
        i_context = check_adjacency(i_context, check_vertical=False)
        if len(i_context) >= min_notes - 1:
            context_dict[i] = i_context
    print('Elapsed time (get context_dict) = %.2f sec' % (time.time() - clkStart))
    print(' len(context_dict.keys()) =', len(context_dict.keys()))
    clkStart = time.time()

    # Get patterns via cotexts
    pattern_dict = {}
    for i in sorted(context_dict.keys()):
        # Get cotexts (co-contexts) of all (i, j) pairs
        cotext_pairs = [
            match_context(i, j, context_dict[i], context_dict[j]) for j in range(i+1, n_notes)
            if (j in context_dict.keys()) and (vTable['ioi'][i, j] >= 2) # and (vTable['ioi'][i, j] < 64)
        ]

        # Delete cotext pairs if size < min_notes and not meet melodic requirments
        cotext_pairs = [pair for pair in cotext_pairs if len(pair[0]) >= min_notes and len(pair[1]) >= min_notes]
        cotext_pairs = [pair for pair in cotext_pairs if melodic_check(pair[0]) and melodic_check(pair[1])]

        if len(cotext_pairs):
            # Find most common cotext
            cotext_pairs = sorted(cotext_pairs, key=lambda pair: len(pair[0]))
            cotext_dict = {tuple(cotext_pairs[0][0]): cotext_pairs[0]}
            for cotext1, cotext2 in cotext_pairs[1:]:
                new_key = tuple(cotext1)
                ckey_cs = [
                    (ckey, cardinality_score(new_key, ckey)) for ckey in cotext_dict.keys()
                ] # similarity between key and ckeys
                max_ckey, max_cs = max(ckey_cs, key=lambda x: x[1])
                if max_cs < min_cardinality:
                    cotext_dict[new_key] = [cotext1, cotext2] # establish a cotext, and its occurrence
                else:
                    cotext_dict[max_ckey] = cotext_dict.pop(max_ckey) + [cotext2] # update cotext and its occurrences

            # Establish a pattern
            key, occurrences = max(cotext_dict.items(), key=lambda t: len(t[1]))
            pattern_dict[key] = sorted(occurrences, key=lambda x: (x[0], len(x)))
    print('Elapsed time (get pattern_dict) = %.2f sec' % (time.time() - clkStart))
    print(' len(pattern_dict.keys())', len(pattern_dict.keys()))
    clkStart = time.time()

    # for k, v in sorted(pattern_dict.items(), key=lambda x: (x[0][0], len(x[0]))):
    #     print(k, v)
    # exit()
    # for key, patterns in sorted(cotext_dict.items(), key=lambda x: x[0][0])[5:]:
        # if key != (5, 9, 10, 11, 15):
        #     continue
    #     for i_p, pattern in enumerate(patterns):
    #         plot_pattern(pattern, notes, plt.subplot(3, 3, i_p+1))
    #     plt.show()
    #     exit()

    # Merge patterns which are adjacent to each other
    def merge_occurrences(os_p, os_m, threshold):
        merge = list(os_m)
        for p in os_p:
            combs = [([p, m], cardinality_score(p, m)) for m in merge]
            pair, cs = max(combs, key=lambda x: x[1])
            if cs > threshold:
                new_m = max(pair, key=lambda x: len(x))
                merge[merge.index(pair[1])] = new_m
            else:
                merge.append(p)
        return sorted(merge, key=lambda x: (x[0], -len(x)))

    # keys = sorted(pattern_dict.keys(), key=lambda k: (-len(k), k[0]))
    # merge_dict = {keys[0]: pattern_dict[keys[0]]}
    # for key in keys[1:]:
    #     pair_cs = [
    #         [(key, mkey), cardinality_score(key, mkey)] for mkey in merge_dict.keys()
    #     ] # similarity between key and mkeys
    #     max_pair, max_cs = max(pair_cs, key=lambda x: x[1])
    #     if max_cs < min_cardinality:
    #         merge_dict[key] = pattern_dict[key] # establish a pattern and its occurrences
    #     else:
    #         occurrences_p = pattern_dict[key]
    #         new_key = max(max_pair, key=lambda x: len(x))
    #         occurrences_m = merge_dict.pop(max_pair[1])
    #         merge_dict[new_key] = merge_occurrences(occurrences_p, occurrences_m, threshold=min_cardinality)
    #         # occurrences = merge_occurrences(occurrences_p, occurrences_m)
    #         # print('occurrences_p', len(occurrences_p), occurrences_p)
    #         # print('occurrences_m', len(occurrences_m), occurrences_m)
    #         # print('occurrences', len(occurrences), occurrences)
    #         # exit()

    pkeys = sorted(pattern_dict.keys(), key=lambda k: k[0])
    merge_dict = {pkeys[0]: pattern_dict[pkeys[0]]}
    for pkey in pkeys[1:]:
        mkey_cs = [
            (mkey, max([cardinality_score(pkey, moccurrence) for moccurrence in moccurrences]))
            for mkey, moccurrences in merge_dict.items()
        ] # similarity between key and mkeys

        max_mkey, max_cs = max(mkey_cs, key=lambda x: x[1])
        if max_cs < min_cardinality:
            merge_dict[pkey] = pattern_dict[pkey] # establish a pattern and its occurrences
        else:
            new_occurrences = merge_occurrences(
                pattern_dict[pkey],
                merge_dict[max_mkey],
                threshold=min_cardinality
            )
            merge_dict[max_mkey] = new_occurrences
    print('Elapsed time (get merge_dict) = %.4f sec' % (time.time() - clkStart))
    print(' len(merge_dict.keys()) =', len(merge_dict.keys()))

    # for key in sorted(merge_dict.keys(), key=lambda k: (k[0], len(k)))[50:]:
        # if key != (5, 9, 10, 11, 15):
        #     continue

    #     patterns = merge_dict[key]
    #     print(key)
    #     print(patterns)
    #     for i_p, pattern in enumerate(patterns):
    #         if i_p < 20:
    #            plot_pattern(pattern, notes, plt.subplot(4, 5, i_p+1))
    #     plt.show()
    #     exit()
    # exit()

    pattern_list = [[list(notes[occur][['onset', 'pitch']]) for occur in occurs] for occurs in merge_dict.values()]
    return pattern_list