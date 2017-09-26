<?php

$qs = preg_replace('/\.+/', '.', $_GET['qs']);
$qs = preg_replace('/^\./', '', $qs);
$qs = preg_replace('/\.$/', '', $qs);

for($i=0;$i<strlen($qs);$i++){
	if(($qs[$i]<'0' || $qs[$i]>'9') && $qs[$i]!='.'){
		die('OAO');
	}
}

$out = shell_exec('/home/keene/anaconda3/envs/StockPattern/bin/python ../PyStockPattern/code_python4web/search.py '.$qs.' 50 60 2');
echo $out;
?>
