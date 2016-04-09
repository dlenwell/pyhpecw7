"""Install an operating system on HPCOM7 devices.
"""
from lxml import etree
from ncclient.xml_ import qualify
from pyhpecw7.utils.xml.namespaces import HPDATA, HPDATA_C, HPACTION
from pyhpecw7.utils.xml.lib import *


class InstallOs(object):
    """This class is used to get and build the startup software image.
    It is often used in conjunction with ``file_copy.FileCopy``, which
    can transfer an image.

    Args:
        device (HPCOM7): connected instance of
            a ``pyhpecw7.comware.HPCOM7`` object.

    Attributes:
        device (HPCOM7): connected instance of
            a ``pyhpecw7.comware.HPCOM7`` object.
    """
    def __init__(self, device):
        self.device = device

    def get_config(self):
        """Return a dictionary of current and startup image names.

        Returns:
            A dictionary of 'current', 'startup-primary', and
            'startup-backup' image file names. For each, there
            is a 'boot' image and a 'system' image::
                {
                    'current': {
                        'boot' : <current boot image>,
                        'system': <current system image>,
                    }
                    'startup-primary': {
                        'boot' : <primary startup boot image>,
                        'system': <primary startup system image>,
                    }
                    'startup-backup': {
                        'boot': <backup startup boot image>,
                        'system': <backup startup system image>
                    }
                }
        """
        E = data_element_maker()
        top = E.top(
            E.Package(
                E.BootLoaderList(
                    E.BootList()
                )
            )
        )

        nc_get_reply = self.device.get(('subtree', top))
        boot_lists = findall_in_data('BootList', nc_get_reply.data_ele)

        image_dict = {}

        key_map = {'0': 'current',
                   '1': 'startup-primary',
                   '2': 'startup-backup'}

        for boot_list in boot_lists:
            list_num = boot_list.findtext(
                './/{0}{1}'.format(HPDATA_C, 'BootType'))
            image_iter = boot_list.iterfind(
                './/{0}{1}'.format(HPDATA_C, 'FileName'))
            try:
                boot_file = image_iter.next().text
                sys_file = image_iter.next().text
            except StopIteration:
                continue

            list_type = key_map[list_num]
            image_dict[list_type] = {}
            image_dict[list_type]['boot'] = boot_file.split(':/')[1]
            image_dict[list_type]['system'] = sys_file.split(':/')[1]

        return image_dict

    def build(self, os_type, ipe=None, boot=None, system=None,
              delete_ipe=False, stage=False):
        """Stage or execute the configuration commands
        for changing the primary startup image.

        Args:
            os_type (str): REQUIRED - 'ipe' (for IPE packages)
                or 'bootsys' (for separate boot and system files.
            ipe (str): REQUIRED if ``os_type`` is 'ipe'
                - The full path of the remote IPE file.
            boot (str): REQUIRED if ``os_type`` is 'bootsys'
                - The full path of the remote boot .bin file.
            system (str): REQUIRED if ``os_type`` is 'bootsys'
                - The full path of the remote system .bin file.
            delete_ipe (bool): OPTIONAL - Whether to delete the remote IPE file
                after config change. Defaults to ``False``.
            stage (bool): whether to stage the commands or execute
                immediately

        Returns:
            True if stage=True and successfully staged
            etree.Element XML response if immediate execution
        """
        E = action_element_maker()

        ipe_params = []
        boot_sys_params = []
        if os_type == 'ipe':
            ipe_params.append(E.IPEFileName(ipe))
            ipe_params.append(E.DeleteIPEFile(str(delete_ipe).lower()))
        elif os_type == 'bootsys':
            boot_sys_ele = E.ImageFiles(
                E.Boot(boot),
                E.System(system)
            )
            boot_sys_params.append(boot_sys_ele)

        top = E.top(
            E.Package(
                E.SetBootImage(
                    E.Type('1'),
                    E.OverwriteLocalFile('false'),
                    *ipe_params
                ),
                *boot_sys_params
            )
        )

        if stage:
            return self.device.stage_config(top, 'action')
        else:
            return self.device.action(top)
