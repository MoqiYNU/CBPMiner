# coding=gbk
from collections import Counter
import copy
import time
import net as nt
import comp_utils as cu
from lts import LTS, Tran
import lts_utils as lu
import mining_utils as mu


# 1.���������----------------------------------------------------------
def CCHP_Discovery(df):

    non_duplicate_df = mu.remove_duplicate_groups(copy.deepcopy(df))
    roles, optional_roles = mu.get_roles(non_duplicate_df)
    print(roles, optional_roles)
    # print(df)
    IHPs = []
    for i, dep in enumerate(roles):
        print('dep', dep)
        sub_df = mu.gen_sub_log(df, dep)
        if dep in optional_roles:
            IHP = mu.IHP_Discovery_all(sub_df, non_duplicate_df, i, True)
        else:
            IHP = mu.IHP_Discovery_all(sub_df, non_duplicate_df, i, False)
        # IHP.net_to_dot('IHP{}'.format(i), False)
        IHPs.append(IHP)

    # �ϲ�����IHP
    comp_net = cu.get_compose_net_async(IHPs)

    # ��dfȷ����ʼ��Դ
    init_res = mu.get_init_res(df, comp_net.res_places)
    comp_net.source = nt.Marking(comp_net.source.get_infor() + init_res)
    comp_net.print_infor()
    # comp_net.net_to_dot('comp_net', False)

    return non_duplicate_df, IHPs, comp_net


# 2.������־����������(ps:log����ȥ��)------------------------------------
def gen_kernel(cases, net: nt.OpenNet):

    source, sinks = net.get_start_ends()

    states = [source]
    gen_trans = []
    for case in cases:
        marking = source
        for enable_tran in case:
            # 1)������̱�ʶ
            preset = nt.get_preset(net.get_flows(), enable_tran)
            postset = nt.get_postset(net.get_flows(), enable_tran)
            succ_makring = nt.succ_marking(marking.get_infor(), preset,
                                           postset)
            # 2)������̱�Ǩ(Note:Ǩ�ƶ����Ա�ǨId���б�ʶ)
            tran = Tran(marking, enable_tran, succ_makring)
            # ���δ���ɵı�ʶ
            if not nt.marking_is_exist(succ_makring, states):
                states.append(succ_makring)
            # ���δ���ɵ�Ǩ��
            if not tran_is_exist(tran, gen_trans):
                gen_trans.append(tran)
            # ps:��Ҫ���ñ�ʶ
            marking = succ_makring

    # ��ֹ��ʶ(ps:������Ϣ��������Դ������Ϊ��)
    end_markings = []
    msg_places = net.msg_places
    res_places = net.res_places
    for marking in states:
        places = marking.get_infor()
        inter_places = [
            place for place in places
            if place not in msg_places and place not in res_places
        ]
        new_marking = nt.Marking(inter_places)
        if nt.marking_is_exist(new_marking, sinks):
            # print('end marking:', places)
            end_markings.append(marking)

    return LTS(source, end_markings, states, gen_trans)


# �Ż��汾������
def gen_kernel_adv(cases, net: nt.OpenNet):

    source, sinks = net.get_start_ends()

    states = [source]
    gen_trans = []
    seq_map = {}
    for case in cases:
        marking = source
        for enable_tran in case:
            # ps:�������*****************************************
            key = frozenset(Counter(marking.get_infor()).items())
            if key in seq_map:
                vals = seq_map[key]
                if enable_tran in vals[0]:
                    index = vals[0].index(enable_tran)
                    marking = vals[1][index]
                else:
                    # 1)������̱�ʶ
                    preset = nt.get_preset(net.get_flows(), enable_tran)
                    postset = nt.get_postset(net.get_flows(), enable_tran)
                    succ_marking = nt.succ_marking(marking.get_infor(), preset,
                                                   postset)
                    # 2)������̱�Ǩ(Note:Ǩ�ƶ����Ա�ǨId���б�ʶ)
                    tran = Tran(marking, enable_tran, succ_marking)
                    gen_trans.append(tran)
                    # print('add 1:', marking.get_infor(), enable_tran,
                    #       succ_marking.get_infor())
                    # ���δ���ɵı�ʶ
                    if not nt.marking_is_exist(succ_marking, states):
                        states.append(succ_marking)
                    vals[0].append(enable_tran)
                    vals[1].append(succ_marking)
                    # ps:��Ҫ���ñ�ʶ
                    marking = succ_marking
            else:
                # 1)������̱�ʶ
                preset = nt.get_preset(net.get_flows(), enable_tran)
                postset = nt.get_postset(net.get_flows(), enable_tran)
                succ_marking = nt.succ_marking(marking.get_infor(), preset,
                                               postset)
                # 2)������̱�Ǩ(Note:Ǩ�ƶ����Ա�ǨId���б�ʶ)
                tran = Tran(marking, enable_tran, succ_marking)
                gen_trans.append(tran)
                # print('add 2:', marking.get_infor(), enable_tran,
                #       succ_marking.get_infor())
                # ���δ���ɵı�ʶ
                if not nt.marking_is_exist(succ_marking, states):
                    states.append(succ_marking)
                seq_map[key] = [[enable_tran], [succ_marking]]
                # ps:��Ҫ���ñ�ʶ
                marking = succ_marking

    # ��ֹ��ʶ(ps:������Ϣ��������Դ������Ϊ��)
    end_markings = []
    msg_places = net.msg_places
    res_places = net.res_places
    for marking in states:
        places = marking.get_infor()
        inter_places = [
            place for place in places
            if place not in msg_places and place not in res_places
        ]
        new_marking = nt.Marking(inter_places)
        if nt.marking_is_exist(new_marking, sinks):
            # print('end marking:', places)
            end_markings.append(marking)

    return LTS(source, end_markings, states, gen_trans)


# �ж�Ǩ���Ƿ��ں��д���
def tran_is_exist(tran: Tran, trans):
    for temp_tran in trans:
        if Counter(temp_tran.state_from.get_infor()) == Counter(
                tran.state_from.get_infor(
                )) and temp_tran.label == tran.label and Counter(
                    temp_tran.state_to.get_infor()) == Counter(
                        tran.state_to.get_infor()):
            return True
    return False


# 3.��ȡ���в��ȶ�����-----------------------------------------------------
def get_unstable_tasks(kernel: LTS, net: nt.OpenNet):
    unstable_tasks = set()
    for marking in kernel.states:
        enable_trans = nt.get_enable_trans(net, marking)
        driver_trans = get_driver_trans(marking, kernel)
        unstable_tasks = unstable_tasks.union(
            set(enable_trans).difference(driver_trans))
    return list(unstable_tasks)


# ��ȡ������marking�����ı�Ǩ��
def get_driver_trans(marking, kernel: LTS):
    driver_trans = set()
    for tran in kernel.trans:
        if nt.equal_markings(tran.state_from, marking):
            driver_trans.add(tran.label)
    return driver_trans


# 4.����ÿ��������֯��Ӧ��Э����-----------------------------------------------
def gen_CDs(nets, kernel: LTS, unstable_tasks):
    hide_kernels = get_hide_kernels(nets, kernel, unstable_tasks)
    CDs = []
    for i, net in enumerate(nets):
        CD_trans = []
        hide_kernel = hide_kernels[i]
        # hide_kernel.lts_to_dot_name('hide_core{}'.format(i))
        min_hide_kernel = lu.min_lts(hide_kernel, i)
        # min_hide_kernel.lts_to_dot_name('min_hide_core{}'.format(i))
        index = 0
        for tran in min_hide_kernel.trans:
            state_from, label, state_to = tran.get_infor()
            if label not in net.trans and label in unstable_tasks:
                cood_state = 'CS{}{}'.format(i, index)
                index += 1
                temp_tran1 = Tran(state_from, 'sync_1_{}'.format(label),
                                  cood_state)
                temp_tran2 = Tran(cood_state, 'sync_2_{}'.format(label),
                                  state_to)
                CD_trans.append(temp_tran1)
                CD_trans.append(temp_tran2)
            elif label in net.trans and label in unstable_tasks:
                cood_state1 = 'CS{}{}'.format(i, index)
                index += 1
                temp_tran1 = Tran(state_from, 'sync_1_{}'.format(label),
                                  cood_state1)
                cood_state2 = 'CS{}{}'.format(i, index)
                index += 1
                temp_tran2 = Tran(cood_state1, label, cood_state2)
                temp_tran3 = Tran(cood_state2, 'sync_2_{}'.format(label),
                                  state_to)
                CD_trans.append(temp_tran1)
                CD_trans.append(temp_tran2)
                CD_trans.append(temp_tran3)
            else:
                CD_trans.append(tran)
        CD_states = []
        for CD_tran in CD_trans:
            state_from, label, state_to = CD_tran.get_infor()
            if state_from not in CD_states:
                CD_states.append(state_from)
            if state_to not in CD_states:
                CD_states.append(state_to)
        CD = LTS(min_hide_kernel.start, min_hide_kernel.ends, CD_states,
                 CD_trans)
        # ��CD״̬����id��ʶ
        CD.start = CD.start.id
        CD.ends = [t.get_infor()[0] for t in CD.ends]
        # print('CD.ends:', CD.ends)
        CDs.append(CD)
    return CDs


# ��ȡ���غ�(����ÿ�����г������Ǩ�������ȶ�������ı�Ǩ����)
# ps:ÿ��״̬�����ַ���������marking
def get_hide_kernels(nets, kernel: LTS, unstable_tasks):
    hide_kernels = []
    start = kernel.start
    ends = kernel.ends
    states = kernel.states
    trans = kernel.trans
    for net in nets:
        # ���ȶ�����������Ǩ��������
        visual_names = unstable_tasks + net.trans
        print('visual_names:', visual_names)
        hide_core_trans = []
        for tran in trans:
            state_from, label, state_to = tran.get_infor()
            if label not in visual_names:
                hide_core_trans.append(Tran(state_from, 'tau', state_to))
            else:
                hide_core_trans.append(tran)
        hide_kernel = LTS(start, ends, states, hide_core_trans)
        hide_kernels.append(hide_kernel)
    return hide_kernels


# 5.���������Ϊ---------------------------------------------
def gen_compose_behavior(comp_net, CDs):

    gen_markings = []
    gen_trans = []
    comp_trans = []

    # ������ʼ���״̬
    init_marking = comp_net.source
    gen_markings.append(init_marking)
    init_CD_state = []
    for lts in CDs:
        start, ends, states, trans = lts.get_infor()
        init_CD_state.append(start)
    init_comp_state = [init_marking, init_CD_state]

    # ���ж��к��ѷ��ʶ���
    visiting_queue = [init_comp_state]
    visited_queue = [init_comp_state]

    # ��������
    while visiting_queue:

        [marking, CD_state] = visiting_queue.pop(0)
        enable_trans = nt.get_enable_trans(comp_net, marking)
        succ_trans = lu.succ_trans(CD_state, CDs)

        for succ_tran in succ_trans:

            state_from, label, state_to = succ_tran.get_infor()

            if label.startswith('sync_'):  # 1)label������Э����Ǩ,��ֻ��Ǩ��CD���
                to_comp_state = [marking, state_to]
                comp_trans.append(
                    Tran([marking, CD_state], label, to_comp_state))
                if not is_visited_comp_state(to_comp_state, visited_queue):
                    visiting_queue.append(to_comp_state)
                    visited_queue.append(to_comp_state)
            else:  #  2)label��Petri���б�Ǩ,ͬʱǨ������Ϻ�CD���
                sync_trans = [tran for tran in enable_trans if tran == label]
                for sync_tran in sync_trans:
                    preset = nt.get_preset(comp_net.get_flows(), sync_tran)
                    postset = nt.get_postset(comp_net.get_flows(), sync_tran)
                    to_marking = nt.succ_marking(marking.get_infor(), preset,
                                                 postset)
                    to_comp_state = [to_marking, state_to]

                    # �������ʹ�����ɵı�ʶ�ͱ�Ǩ
                    if not nt.marking_is_exist(to_marking, gen_markings):
                        gen_markings.append(to_marking)
                    gen_trans.append(Tran(marking, label, to_marking))
                    # ���ɵ������Ϊ�ı�ʶ�ͱ�Ǩ
                    comp_trans.append(
                        Tran([marking, CD_state], label, to_comp_state))
                    if not is_visited_comp_state(to_comp_state, visited_queue):
                        visiting_queue.append(to_comp_state)
                        visited_queue.append(to_comp_state)

    # ��ֹ��ʶ(ps:������Ϣ��������Դ������Ϊ��)
    end_markings = []
    for marking in gen_markings:
        if is_end_marking(marking, comp_net):
            end_markings.append(marking)
    gen_behavior = LTS(init_marking, end_markings, gen_markings, gen_trans)

    # �����ֹ״̬
    comp_ends = []
    for comp_state in visited_queue:
        if is_end_marking(comp_state[0], comp_net) and lu.is_comp_ends(
                comp_state[1], CDs):
            print('ends:', comp_state[0].get_infor(), comp_state[1])
            comp_ends.append(comp_state)
    comp_behavior = LTS(init_comp_state, comp_ends, visited_queue, comp_trans)

    return gen_behavior, comp_behavior


def is_visited_comp_state(comp_state, visited_queue):
    for temp_comp_state in visited_queue:
        if nt.equal_markings(
                temp_comp_state[0],
                comp_state[0]) and temp_comp_state[1] == comp_state[1]:
            return True
    return False


# �ж���ϱ�ʶ�Ƿ�Ϊ��ֹ��ʶ(������Ϣ����Դ����)
def is_end_marking(marking, comp_net):
    msg_places = comp_net.msg_places
    res_places = comp_net.res_places
    places = marking.get_infor()
    inter_places = [
        place for place in places
        if place not in msg_places and place not in res_places
    ]
    new_marking = nt.Marking(inter_places)
    if nt.marking_is_exist(new_marking, comp_net.sinks):
        return True
    return False


if __name__ == '__main__':

    # csv_file = 'log_files/LOG.csv'
    csv_file = 'log_files/PO_Log.csv'
    # i = '04'
    # csv_file = 'log_files/Log_{}.csv'.format(i)
    df = mu.csv_to_df(csv_file)

    start_time = time.time()

    non_duplicate_df, nets, comp_net = CCHP_Discovery(df)

    cases = mu.gen_cases(non_duplicate_df)
    # print(cases)
    kernel = gen_kernel_adv(cases, comp_net)

    unstable_tasks = get_unstable_tasks(kernel, comp_net)
    print('unstable_tasks:', unstable_tasks)

    # ps:��kernel��Ҫת��ΪLTS
    kernel = kernel.rg_to_lts()[0]
    kernel.lts_to_dot()

    CDs = gen_CDs(nets, kernel, unstable_tasks)
    # # for i, CD in enumerate(CDs):
    # #     CD.lts_to_dot_name('CD{}'.format(i))

    end_time = time.time()
    print('time_cost:', end_time - start_time)

    gen_behavior, comp_behavior = gen_compose_behavior(comp_net, CDs)
    gen_behavior_lts, marking_map = gen_behavior.rg_to_lts()
    gen_behavior_lts.lts_to_dot_name('gen_behavior')
    # comp_behavior_lts, comp_state_map = comp_behavior.comp_to_lts()
    # comp_behavior_lts.lts_to_dot_name('comp_behavior')

    # ���Ժķ�ƽ��ʱ��
    # with open('log_files/results.csv', 'a') as f:
    #     # д�뷽�����ֵ�results.csv
    #     f.write('method: Ours\n')

    # for i in range(1, 13):
    #     # ���С��10��ôǰ���0������ֱ�ӷ���
    #     if i < 10:
    #         i = '0' + str(i)
    #     csv_file = 'log_files/Log_{}.csv'.format(i)
    #     df = mu.csv_to_df(csv_file)
    #     # ����ķѵ�ʱ��
    #     time_cost = 0
    #     for j in range(10):
    #         print('j:', j)
    #         start_time = time.time()
    #         non_duplicate_df, nets, comp_net = CCHP_Discovery(df)
    #         cases = mu.gen_cases(non_duplicate_df)
    #         kernel = gen_kernel(cases, comp_net)
    #         unstable_tasks = get_unstable_tasks(kernel, comp_net)
    #         # ps:��kernel��Ҫת��ΪLTS
    #         kernel = kernel.rg_to_lts()[0]
    #         CDs = gen_CDs(nets, kernel, unstable_tasks)
    #         end_time = time.time()
    #         time_cost += end_time - start_time
    #     with open('log_files/results.csv', 'a') as f:
    #         f.write('Log-{}: time_cost: {}\n'.format(i, time_cost / 10))
