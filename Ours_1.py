# coding=gbk
from collections import Counter
import copy
import time
import net as nt
import comp_utils as cu
from lts import LTS, Tran
import lts_utils as lu
import mining_utils as mu


# 1.发现组合网----------------------------------------------------------
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

    # 合并所有IHP
    comp_net = cu.get_compose_net_async(IHPs)

    # 由df确定初始资源
    init_res = mu.get_init_res(df, comp_net.res_places)
    comp_net.source = nt.Marking(comp_net.source.get_infor() + init_res)
    comp_net.print_infor()
    # comp_net.net_to_dot('comp_net', False)

    return non_duplicate_df, IHPs, comp_net


# 2.利用日志引导产生核(ps:log首先去重)------------------------------------
def gen_kernel(cases, net: nt.OpenNet):

    source, sinks = net.get_start_ends()

    states = [source]
    gen_trans = []
    for case in cases:
        marking = source
        for enable_tran in case:
            # 1)产生后继标识
            preset = nt.get_preset(net.get_flows(), enable_tran)
            postset = nt.get_postset(net.get_flows(), enable_tran)
            succ_makring = nt.succ_marking(marking.get_infor(), preset,
                                           postset)
            # 2)产生后继变迁(Note:迁移动作以变迁Id进行标识)
            tran = Tran(marking, enable_tran, succ_makring)
            # 添加未生成的标识
            if not nt.marking_is_exist(succ_makring, states):
                states.append(succ_makring)
            # 添加未生成的迁移
            if not tran_is_exist(tran, gen_trans):
                gen_trans.append(tran)
            # ps:需要重置标识
            marking = succ_makring

    # 终止标识(ps:允许消息库所和资源库所不为空)
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


# 优化版本产生核
def gen_kernel_adv(cases, net: nt.OpenNet):

    source, sinks = net.get_start_ends()

    states = [source]
    gen_trans = []
    seq_map = {}
    for case in cases:
        marking = source
        for enable_tran in case:
            # ps:无序情况*****************************************
            key = frozenset(Counter(marking.get_infor()).items())
            if key in seq_map:
                vals = seq_map[key]
                if enable_tran in vals[0]:
                    index = vals[0].index(enable_tran)
                    marking = vals[1][index]
                else:
                    # 1)产生后继标识
                    preset = nt.get_preset(net.get_flows(), enable_tran)
                    postset = nt.get_postset(net.get_flows(), enable_tran)
                    succ_marking = nt.succ_marking(marking.get_infor(), preset,
                                                   postset)
                    # 2)产生后继变迁(Note:迁移动作以变迁Id进行标识)
                    tran = Tran(marking, enable_tran, succ_marking)
                    gen_trans.append(tran)
                    # print('add 1:', marking.get_infor(), enable_tran,
                    #       succ_marking.get_infor())
                    # 添加未生成的标识
                    if not nt.marking_is_exist(succ_marking, states):
                        states.append(succ_marking)
                    vals[0].append(enable_tran)
                    vals[1].append(succ_marking)
                    # ps:需要重置标识
                    marking = succ_marking
            else:
                # 1)产生后继标识
                preset = nt.get_preset(net.get_flows(), enable_tran)
                postset = nt.get_postset(net.get_flows(), enable_tran)
                succ_marking = nt.succ_marking(marking.get_infor(), preset,
                                               postset)
                # 2)产生后继变迁(Note:迁移动作以变迁Id进行标识)
                tran = Tran(marking, enable_tran, succ_marking)
                gen_trans.append(tran)
                # print('add 2:', marking.get_infor(), enable_tran,
                #       succ_marking.get_infor())
                # 添加未生成的标识
                if not nt.marking_is_exist(succ_marking, states):
                    states.append(succ_marking)
                seq_map[key] = [[enable_tran], [succ_marking]]
                # ps:需要重置标识
                marking = succ_marking

    # 终止标识(ps:允许消息库所和资源库所不为空)
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


# 判断迁移是否在核中存在
def tran_is_exist(tran: Tran, trans):
    for temp_tran in trans:
        if Counter(temp_tran.state_from.get_infor()) == Counter(
                tran.state_from.get_infor(
                )) and temp_tran.label == tran.label and Counter(
                    temp_tran.state_to.get_infor()) == Counter(
                        tran.state_to.get_infor()):
            return True
    return False


# 3.获取核中不稳定任务集-----------------------------------------------------
def get_unstable_tasks(kernel: LTS, net: nt.OpenNet):
    unstable_tasks = set()
    for marking in kernel.states:
        enable_trans = nt.get_enable_trans(net, marking)
        driver_trans = get_driver_trans(marking, kernel)
        unstable_tasks = unstable_tasks.union(
            set(enable_trans).difference(driver_trans))
    return list(unstable_tasks)


# 获取核中由marking引出的变迁集
def get_driver_trans(marking, kernel: LTS):
    driver_trans = set()
    for tran in kernel.trans:
        if nt.equal_markings(tran.state_from, marking):
            driver_trans.add(tran.label)
    return driver_trans


# 4.产生每个参与组织对应的协调者-----------------------------------------------
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
        # 将CD状态都以id标识
        CD.start = CD.start.id
        CD.ends = [t.get_infor()[0] for t in CD.ends]
        # print('CD.ends:', CD.ends)
        CDs.append(CD)
    return CDs


# 获取隐藏核(即将每个网中除自身变迁集及不稳定任务外的变迁隐藏)
# ps:每个状态都是字符串而不是marking
def get_hide_kernels(nets, kernel: LTS, unstable_tasks):
    hide_kernels = []
    start = kernel.start
    ends = kernel.ends
    states = kernel.states
    trans = kernel.trans
    for net in nets:
        # 不稳定任务和自身变迁不能隐藏
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


# 5.产生组合行为---------------------------------------------
def gen_compose_behavior(comp_net, CDs):

    gen_markings = []
    gen_trans = []
    comp_trans = []

    # 构建初始组合状态
    init_marking = comp_net.source
    gen_markings.append(init_marking)
    init_CD_state = []
    for lts in CDs:
        start, ends, states, trans = lts.get_infor()
        init_CD_state.append(start)
    init_comp_state = [init_marking, init_CD_state]

    # 运行队列和已访问队列
    visiting_queue = [init_comp_state]
    visited_queue = [init_comp_state]

    # 迭代计算
    while visiting_queue:

        [marking, CD_state] = visiting_queue.pop(0)
        enable_trans = nt.get_enable_trans(comp_net, marking)
        succ_trans = lu.succ_trans(CD_state, CDs)

        for succ_tran in succ_trans:

            state_from, label, state_to = succ_tran.get_infor()

            if label.startswith('sync_'):  # 1)label是引入协调变迁,则只需迁移CD组合
                to_comp_state = [marking, state_to]
                comp_trans.append(
                    Tran([marking, CD_state], label, to_comp_state))
                if not is_visited_comp_state(to_comp_state, visited_queue):
                    visiting_queue.append(to_comp_state)
                    visited_queue.append(to_comp_state)
            else:  #  2)label是Petri网中变迁,同时迁移网组合和CD组合
                sync_trans = [tran for tran in enable_trans if tran == label]
                for sync_tran in sync_trans:
                    preset = nt.get_preset(comp_net.get_flows(), sync_tran)
                    postset = nt.get_postset(comp_net.get_flows(), sync_tran)
                    to_marking = nt.succ_marking(marking.get_infor(), preset,
                                                 postset)
                    to_comp_state = [to_marking, state_to]

                    # 组合网迫使后生成的标识和变迁
                    if not nt.marking_is_exist(to_marking, gen_markings):
                        gen_markings.append(to_marking)
                    gen_trans.append(Tran(marking, label, to_marking))
                    # 生成的组合行为的标识和变迁
                    comp_trans.append(
                        Tran([marking, CD_state], label, to_comp_state))
                    if not is_visited_comp_state(to_comp_state, visited_queue):
                        visiting_queue.append(to_comp_state)
                        visited_queue.append(to_comp_state)

    # 终止标识(ps:允许消息库所和资源库所不为空)
    end_markings = []
    for marking in gen_markings:
        if is_end_marking(marking, comp_net):
            end_markings.append(marking)
    gen_behavior = LTS(init_marking, end_markings, gen_markings, gen_trans)

    # 组合终止状态
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


# 判断组合标识是否为终止标识(容许消息和资源存在)
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

    # ps:将kernel需要转化为LTS
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

    # 测试耗费平均时间
    # with open('log_files/results.csv', 'a') as f:
    #     # 写入方法名字到results.csv
    #     f.write('method: Ours\n')

    # for i in range(1, 13):
    #     # 如果小于10那么前面加0，否则直接返回
    #     if i < 10:
    #         i = '0' + str(i)
    #     csv_file = 'log_files/Log_{}.csv'.format(i)
    #     df = mu.csv_to_df(csv_file)
    #     # 计算耗费的时间
    #     time_cost = 0
    #     for j in range(10):
    #         print('j:', j)
    #         start_time = time.time()
    #         non_duplicate_df, nets, comp_net = CCHP_Discovery(df)
    #         cases = mu.gen_cases(non_duplicate_df)
    #         kernel = gen_kernel(cases, comp_net)
    #         unstable_tasks = get_unstable_tasks(kernel, comp_net)
    #         # ps:将kernel需要转化为LTS
    #         kernel = kernel.rg_to_lts()[0]
    #         CDs = gen_CDs(nets, kernel, unstable_tasks)
    #         end_time = time.time()
    #         time_cost += end_time - start_time
    #     with open('log_files/results.csv', 'a') as f:
    #         f.write('Log-{}: time_cost: {}\n'.format(i, time_cost / 10))
