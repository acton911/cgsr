#!/bin/sh
cd /sys/bus/pci/drivers/xhci_hcd
devices=$(ls | grep :)

echo "Unbinding devices:"
echo -n "$devices"
echo
for i in $devices
do
    echo $i > unbind
done

echo "Binding devices"
for i in $devices
do
    echo $i > bind
done
