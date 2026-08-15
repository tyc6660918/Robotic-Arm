**常用构建与烧录命令**

```c
 make build
./esputil mkhex 0x8000 build/partition_table/partition-table.bin 0x1000 build/bootloader/bootloader.bin 0x100000 build/mongoose-esp32-example.bin > bridge.hex
./esputil -fspi 6,17,8,11,16  -p /dev/cu.usbserial-0001 flash bridge.hex
```

参考资料
https://mongoose.ws/documentation/tutorials/uart-bridge/
