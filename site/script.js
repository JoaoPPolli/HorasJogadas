'use strict';
// Escolhe apenas o rótulo do botão principal. Nenhum download é iniciado sem clique.
(() => {
  const link = document.getElementById('primary-download');
  const platform = navigator.userAgentData?.platform || navigator.platform || '';
  if (/Linux/i.test(platform) && !/Android/i.test(navigator.userAgent)) {
    link.href = link.href.replace('HorasJogadas-Windows-Setup.exe', 'HorasJogadas-Linux-x86_64.tar.gz');
    link.querySelector('span').textContent = 'Baixar para Linux';
  } else if (!/Win/i.test(platform)) {
    link.href = '#download';
    link.querySelector('span').textContent = 'Escolher meu sistema';
  }
})();
