#!/usr/bin/env bash
# Mount the PC's (192.168.0.115) SSD at /mnt/ssd. Asks for the PC's sudo password.
ssh -t sam@192.168.0.115 'sudo mount -t ntfs3 -o uid=1000,gid=1000,dmask=0022,fmask=0022,force,windows_names,iocharset=utf8,prealloc /dev/nvme0n1p8 /mnt/ssd && findmnt /mnt/ssd && df -h /mnt/ssd'
