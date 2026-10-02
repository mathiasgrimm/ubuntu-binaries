<?php
// Verify the Ubuntu PHP extension can invoke the bundled FFmpeg delegate.
putenv('PATH=/opt/bin:'.getenv('PATH'));
$path = tempnam(sys_get_temp_dir(), 'apng');
try {
    $command = '/opt/bin/ffmpeg -nostdin -v error -f lavfi -i '.escapeshellarg('testsrc=size=16x16:rate=2').' -frames:v 3 -plays 1 -f apng -y '.escapeshellarg($path);
    passthru($command, $exit);
    if ($exit !== 0) { throw new RuntimeException('APNG fixture failed'); }
    $image = new Imagick;
    $image->setOption('video:intermediate-format', 'pam');
    $image->readImage('apng:'.$path);
    if ($image->getNumberImages() !== 3) { throw new RuntimeException('Lost APNG frames'); }
    $image->clear();
    echo Imagick::getVersion()['versionString'], "\nUbuntu PHP Imagick APNG delegate passed\n";
} finally {
    unlink($path);
}
