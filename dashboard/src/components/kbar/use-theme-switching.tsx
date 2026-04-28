import { useRegisterActions } from 'kbar';
import { useShellStore } from '@/stores/shell-store';

const useThemeSwitching = () => {
  const { theme, setTheme, density, setDensity, sidebar, toggleSidebar } = useShellStore();

  const actions = [
    {
      id: 'toggleTheme',
      name: 'Toggle Theme',
      shortcut: ['t', 't'],
      section: 'Theme',
      perform: () => setTheme(theme === 'light' ? 'dark' : 'light')
    },
    { id: 'setLightTheme', name: 'Set Light Theme', section: 'Theme', perform: () => setTheme('light') },
    { id: 'setDarkTheme', name: 'Set Dark Theme', section: 'Theme', perform: () => setTheme('dark') },
    { id: 'setTight', name: 'Density: Tight', section: 'Density', perform: () => setDensity('tight') },
    { id: 'setComfy', name: 'Density: Comfortable', section: 'Density', perform: () => setDensity('comfortable') },
    { id: 'setSpacious', name: 'Density: Spacious', section: 'Density', perform: () => setDensity('spacious') },
    { id: 'toggleSidebar', name: 'Toggle Sidebar', section: 'Layout', perform: () => toggleSidebar() }
  ];

  useRegisterActions(actions, [theme, density, sidebar]);
};

export default useThemeSwitching;
