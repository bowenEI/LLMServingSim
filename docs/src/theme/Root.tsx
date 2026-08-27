import React, {type ReactNode} from 'react';
import Head from '@docusaurus/Head';
import {useLocation} from '@docusaurus/router';

export default function Root({children}: {children: ReactNode}): ReactNode {
  const {pathname} = useLocation();
  const htmlLang = pathname === '/zh' || pathname.startsWith('/zh/')
    ? 'zh-CN'
    : 'en';

  return (
    <>
      <Head>
        <html lang={htmlLang} />
      </Head>
      {children}
    </>
  );
}
