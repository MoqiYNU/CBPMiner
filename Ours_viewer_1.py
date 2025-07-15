# coding=gbk
from pywebio.input import input_group, file_upload, actions
from pywebio.output import put_image, put_markdown, use_scope, clear, put_text, put_info, put_success
import Ours_1 as ou
import os
import mining_utils as mu


# ��շ������ļ���
def del_files(path):
    ls = os.listdir(path)
    for i in ls:
        c_path = os.path.join(path, i)
        if os.path.isdir(c_path):
            del_files(c_path)
        else:
            os.remove(c_path)


# 1.����scope����ʾ������ͨ·,����ȡ�����������ݲ���-----------------
with use_scope('Top'):
    # ����Ӵִ�д
    put_markdown(r""" # <center>CBP Miner """).show()
    # ����ָ���
    # put_markdown(r""" ___ """).show()
    with use_scope('output'):
        put_markdown(r""" </br> """).show()
        put_info('The discovered CBP and CDs will be presented here.')
        put_text('')
        put_image('')

    info = input_group('Request form', [
        file_upload("Please upload an event log in CSV format:",
                    name='log',
                    placeholder='Choose file',
                    accept=".csv,.txt,.pdf,.jpg",
                    required=True),
        actions('', [
            {
                'label': 'Generate',
                'value': 'generate'
            },
        ],
                name='action'),
    ])

# 2.ͨ��ѭ����������,Ȼ�����������ͨ·----------------------------
while info is not None:
    if info['action'] == 'generate':

        # a.��ձ��ط������ļ���
        del_files('/Users/moqi/VSCodeProjects/file server')
        # b.�����ʾͨ·��Χ
        clear(scope='Top')

        # c.��д���ļ�������
        log_name = info['log'].get('filename')
        log_path = '/Users/moqi/VSCodeProjects/file server/{}'.format(log_name)
        with open(log_path, mode='wb') as f:
            f.write(info['log'].get('content'))

        # d.��������CDs
        non_duplicate_df, nets, comp_net = mu.CCHP_Discovery(log_path)

        cases = mu.gen_cases(non_duplicate_df)
        kernel = ou.gen_kernel(cases, comp_net)

        unstable_tasks = ou.get_unstable_tasks(kernel, comp_net)
        print('unstable_tasks:', unstable_tasks)

        # ps:��kernel��Ҫת��ΪLTS
        kernel = kernel.rg_to_lts()[0]
        # kernel.lts_to_dot()
        CDs = ou.gen_CDs(nets, kernel, unstable_tasks)

        # e.����jpgͼ��
        net_path = '/Users/moqi/VSCodeProjects/file server/{}'.format(
            'comp_net')
        comp_net.net_to_dot(net_path, False)
        for i, CD in enumerate(CDs):
            cd_path = '/Users/moqi/VSCodeProjects/file server/CD{}'.format(i)
            CD.lts_to_dot_name(cd_path)

        # Note:���ö�ȡ�����Ƶ�rbģʽ
        img = open(net_path + '.jpg', 'rb').read()

        with use_scope('Top'):
            # ����Ӵִ�д����
            put_markdown(r""" # <center>CBP Miner """).show()
            # f.��ͼ����ʾ�ڷ�Χ��
            with use_scope('output'):
                put_success('Discovered CBP:')
                put_image(img)
                # ������
                put_markdown(r""" <br/> """).show()
                put_markdown(r""" <br/> """).show()
                put_success(' CDs ({})'.format(len((CDs))))
                for index in range(0, len(CDs)):
                    cd_path = '/Users/moqi/VSCodeProjects/file server/CD{}.gv'.format(
                        index)
                    # Note:���ö�ȡ�����Ƶ�rbģʽ
                    img = open(cd_path + '.jpg', 'rb').read()
                    put_image(img)
            # g.������������
            info = input_group('Request form', [
                file_upload("Please upload an event log in CSV format:",
                            name='log',
                            placeholder='Choose file',
                            accept=".csv,.txt,.pdf,.jpg",
                            required=True),
                actions('', [
                    {
                        'label': 'Generate',
                        'value': 'generate'
                    },
                ],
                        name='action'),
            ])
