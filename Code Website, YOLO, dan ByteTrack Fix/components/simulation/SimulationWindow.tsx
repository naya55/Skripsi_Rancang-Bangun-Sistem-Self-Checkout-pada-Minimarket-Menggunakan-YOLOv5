'use client';

import { useState } from 'react';
import { useSocket } from '@/hooks/useSocket';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import DraggableWindow from '@/components/ui/draggable-window';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Gamepad2, Plus, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Target, Trash2 } from 'lucide-react';
import { PRODUCT_OPTIONS } from '@/lib/constants';

export default function SimulationWindow() {
  const socket = useSocket();
  const [open, setOpen] = useState(false);
  const [newObject, setNewObject] = useState({
    label: '',
    x: 50,
    y: 50,
    width: 80,
    height: 80
  });

  const handleAddObject = () => {
    if (newObject.label) {
      socket.addSimulatedObject(newObject);
      setNewObject({
        label: '',
        x: 50,
        y: 50,
        width: 80,
        height: 80
      });
    }
  };

  const handleMoveObject = (objId: string, direction: string) => {
    socket.moveSimulatedObject(objId, direction, 15);
  };

  const handleMoveToZone = (objId: string) => {
    socket.moveToZone(objId);
  };

  const handleRemoveObject = (objId: string) => {
    socket.removeSimulatedObject(objId);
  };

  const simulatedObjectEntries = Object.entries(socket.simulatedObjects);

  if (!socket.isSimulationMode) {
    return null;
  }

  return (
    <>
      <div className="fixed bottom-4 right-4 z-50">
        <Button 
          className="bg-orange-500 hover:bg-orange-600 text-white shadow-lg"
          onClick={() => setOpen(true)}
        >
          <Gamepad2 className="h-4 w-4 mr-2" />
          Kontrol Simulasi
        </Button>
      </div>
      
      <DraggableWindow
        title="Panel Kontrol Mode Simulasi"
        icon={<Gamepad2 className="h-5 w-5 text-orange-500" />}
        isOpen={open}
        onClose={() => setOpen(false)}
        defaultPosition={{ x: 200, y: 200 }}
        defaultSize={{ width: '800px', height: '650px' }}
        minWidth="600px"
        minHeight="500px"
        noBackdrop={true}
      >

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Tambah Objek Virtual
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Product Type</Label>
                <Select
                  value={newObject.label}
                  onValueChange={(value) => setNewObject({ ...newObject, label: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select product type" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRODUCT_OPTIONS.map((product) => (
                      <SelectItem key={product} value={product}>
                        {product.charAt(0).toUpperCase() + product.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>X Position</Label>
                  <Input
                    type="number"
                    value={newObject.x}
                    onChange={(e) => setNewObject({ ...newObject, x: parseInt(e.target.value) || 0 })}
                    min="0"
                    max="640"
                  />
                </div>
                <div>
                  <Label>Y Position</Label>
                  <Input
                    type="number"
                    value={newObject.y}
                    onChange={(e) => setNewObject({ ...newObject, y: parseInt(e.target.value) || 0 })}
                    min="0"
                    max="480"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Width</Label>
                  <Input
                    type="number"
                    value={newObject.width}
                    onChange={(e) => setNewObject({ ...newObject, width: parseInt(e.target.value) || 0 })}
                    min="20"
                    max="200"
                  />
                </div>
                <div>
                  <Label>Height</Label>
                  <Input
                    type="number"
                    value={newObject.height}
                    onChange={(e) => setNewObject({ ...newObject, height: parseInt(e.target.value) || 0 })}
                    min="20"
                    max="200"
                  />
                </div>
              </div>

              <Button 
                onClick={handleAddObject}
                className="w-full"
                disabled={!newObject.label}
              >
                <Plus className="h-4 w-4 mr-2" />
                Tambah Objek Virtual
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Virtual Objects</CardTitle>
            </CardHeader>
            <CardContent>
              {simulatedObjectEntries.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Gamepad2 className="h-12 w-12 mx-auto mb-3 text-muted-foreground/50" />
                  <p>No virtual objects</p>
                  <p className="text-sm">Add objects to test detection</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {simulatedObjectEntries.map(([objId, obj]) => (
                    <div key={objId} className="border rounded-lg p-3 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <Badge variant="outline" className="capitalize">
                            {obj.label}
                          </Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            Position: ({obj.x}, {obj.y}) Size: {obj.width}×{obj.height}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemoveObject(objId)}
                          className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>

                      <Separator />

                      <div className="space-y-2">
                        <div className="flex items-center justify-center">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMoveObject(objId, 'up')}
                          >
                            <ArrowUp className="h-3 w-3" />
                          </Button>
                        </div>
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMoveObject(objId, 'left')}
                          >
                            <ArrowLeft className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleMoveToZone(objId)}
                            className="bg-blue-500 hover:bg-blue-600 text-white dark:bg-blue-600 dark:hover:bg-blue-700"
                          >
                            <Target className="h-3 w-3 mr-1" />
                            Zone
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMoveObject(objId, 'right')}
                          >
                            <ArrowRight className="h-3 w-3" />
                          </Button>
                        </div>
                        <div className="flex items-center justify-center">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMoveObject(objId, 'down')}
                          >
                            <ArrowDown className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Gamepad2 className="h-5 w-5 text-orange-600 dark:text-orange-400 mt-0.5" />
            <div>
              <h4 className="font-medium text-orange-900 dark:text-orange-100">Simulation Mode Instructions</h4>
              <p className="text-sm text-orange-700 dark:text-orange-300 mt-1">
                Add virtual objects to test the detection system without real products. 
                Use movement controls to simulate objects passing through the counting zone.
              </p>
            </div>
          </div>
        </div>
      </DraggableWindow>
    </>
  );
}