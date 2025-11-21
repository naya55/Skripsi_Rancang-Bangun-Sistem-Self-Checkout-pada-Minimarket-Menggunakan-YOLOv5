'use client';

import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Gamepad2 } from 'lucide-react';

export default function SimulationToggle() {
  const socket = useSocket();

  const handleSimulationToggle = () => {
    socket.toggleSimulation(!socket.isSimulationMode);
  };

  return (
    <Button 
      variant={socket.isSimulationMode ? "default" : "outline"}
      size="icon"
      onClick={handleSimulationToggle}
      disabled={!socket.isConnected}
    >
      <Gamepad2 className="h-4 w-4" />
    </Button>
  );
}