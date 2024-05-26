import { Welcome } from '../components/Welcome/Welcome';
import { ColorSchemeToggle } from '../components/ColorSchemeToggle/ColorSchemeToggle';
import { LeadGrid } from '@/components/LeadGrid/LeadGrid';

export default function HomePage() {
  return (
    <>
      <Welcome />
      <ColorSchemeToggle />
      <LeadGrid />
    </>
  );
}
