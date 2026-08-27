import React, {type ReactNode} from 'react';
import DefaultNavbarItem from '@theme/NavbarItem/DefaultNavbarItem';
import DropdownNavbarItem from '@theme/NavbarItem/DropdownNavbarItem';
import LocaleDropdownNavbarItem from '@theme/NavbarItem/LocaleDropdownNavbarItem';
import SearchNavbarItem from '@theme/NavbarItem/SearchNavbarItem';
import HtmlNavbarItem from '@theme/NavbarItem/HtmlNavbarItem';
import DocNavbarItem from '@theme/NavbarItem/DocNavbarItem';
import DocSidebarNavbarItem from '@theme/NavbarItem/DocSidebarNavbarItem';
import DocsVersionNavbarItem from '@theme/NavbarItem/DocsVersionNavbarItem';
import DocsVersionDropdownNavbarItem from '@theme/NavbarItem/DocsVersionDropdownNavbarItem';
import {useLocation} from '@docusaurus/router';
import type {ComponentTypesObject} from '@theme/NavbarItem/ComponentTypes';

type LanguageSwitcherProps = {
  mobile?: boolean;
  position?: 'left' | 'right';
  className?: string;
  onClick?: () => void;
};

function localizedPath(pathname: string, locale: 'en' | 'zh'): string {
  // Preserve the current document when browsing either documentation tree.
  // Non-document pages (home, contact, changelog) have no translations yet,
  // so switch those to the selected language's documentation home instead of
  // creating a dead /en/contact or /zh/contact URL.
  if (!/^\/(?:en|zh)(?:\/|$)/.test(pathname) || pathname.includes('/category/')) {
    return `/${locale}`;
  }
  const path = pathname.replace(/^\/(?:en|zh)(?=\/|$)/, '') || '/';
  return `/${locale}${path === '/' ? '' : path}`;
}

function LanguageSwitcher({
  mobile = false,
  position,
  className,
  onClick,
}: LanguageSwitcherProps): ReactNode {
  const {pathname} = useLocation();
  const currentLocale = pathname === '/zh' || pathname.startsWith('/zh/') ? 'zh' : 'en';
  const label = currentLocale === 'zh' ? '中文' : 'English';

  return (
    <DropdownNavbarItem
      mobile={mobile}
      position={position}
      className={className}
      label={label}
      onClick={onClick}
      items={[
        {
          label: 'English',
          to: localizedPath(pathname, 'en'),
          target: '_self',
          autoAddBaseUrl: false,
          lang: 'en',
        },
        {
          label: '中文',
          to: localizedPath(pathname, 'zh'),
          target: '_self',
          autoAddBaseUrl: false,
          lang: 'zh-CN',
        },
      ]}
    />
  );
}

const ComponentTypes: ComponentTypesObject = {
  default: DefaultNavbarItem,
  localeDropdown: LocaleDropdownNavbarItem,
  search: SearchNavbarItem,
  dropdown: DropdownNavbarItem,
  html: HtmlNavbarItem,
  doc: DocNavbarItem,
  docSidebar: DocSidebarNavbarItem,
  docsVersion: DocsVersionNavbarItem,
  docsVersionDropdown: DocsVersionDropdownNavbarItem,
  'custom-languageSwitcher': LanguageSwitcher,
};

export default ComponentTypes;
