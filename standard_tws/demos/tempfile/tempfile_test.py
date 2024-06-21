from tempfile import TemporaryDirectory


with TemporaryDirectory() as dirname:
    print('dirname is:', dirname)
